import json
import hashlib
import re
from pathlib import Path
from collections import Counter, defaultdict


# ============================================================
# CONFIG
# ============================================================

INPUT_FILE = Path("processed/clean/clean_pages.jsonl")
OUTPUT_DIR = Path("processed/chunks")

OUTPUT_FILE = OUTPUT_DIR / "chunks.jsonl"
STATS_FILE = OUTPUT_DIR / "chunk_stats.json"

# Normal chunk size
TARGET_WORDS = 800

# Hard maximum
MAX_WORDS = 1100

# Overlap between consecutive chunks
OVERLAP_WORDS = 100

# IMPORTANT:
# Do not allow a chunk to span too many pages.
# This prevents slide/caption PDFs from becoming one huge chunk.
MAX_PAGES_PER_CHUNK = 5


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize_text(text):
    """Light normalization without destroying useful structure."""

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")
    text = text.replace("\x00", "")

    # Collapse spaces/tabs but keep newlines.
    text = re.sub(r"[ \t]+", " ", text)

    # Avoid huge blank-line gaps.
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def split_paragraphs(text):
    """
    Split text primarily using paragraph boundaries.
    """

    text = normalize_text(text)

    if not text:
        return []

    paragraphs = re.split(r"\n\s*\n", text)

    result = []

    for paragraph in paragraphs:

        paragraph = paragraph.strip()

        if not paragraph:
            continue

        result.append(paragraph)

    return result


def split_long_text(text, max_words=MAX_WORDS):
    """
    Split very long blocks so that no individual block
    becomes excessively large.
    """

    words = text.split()

    if len(words) <= max_words:
        return [text]

    pieces = []

    for i in range(0, len(words), max_words):
        piece = " ".join(words[i:i + max_words])

        if piece.strip():
            pieces.append(piece)

    return pieces


def word_count(text):
    return len(text.split())


def make_content_hash(text):
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def make_chunk_id(source_path, chunk_index, text):
    raw = f"{source_path}|{chunk_index}|{text}"

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:24]


# ============================================================
# LOAD CLEAN PAGES
# ============================================================

def load_pages():

    pages = []

    with INPUT_FILE.open(
        "r",
        encoding="utf-8"
    ) as f:

        for line_number, line in enumerate(f, 1):

            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)

            except json.JSONDecodeError:

                print(
                    f"WARNING: invalid JSON at line "
                    f"{line_number}"
                )

                continue

            text = record.get("text", "")

            if not text or not text.strip():
                continue

            pages.append(record)

    return pages


# ============================================================
# CHUNK ONE DOCUMENT
# ============================================================

def chunk_document(page_records):

    chunks = []

    current_blocks = []
    current_words = 0

    chunk_page_start = None
    chunk_page_end = None

    chunk_index = 0

    source_path = page_records[0].get(
        "source_path",
        ""
    )

    def flush_chunk():

        nonlocal current_blocks
        nonlocal current_words
        nonlocal chunk_page_start
        nonlocal chunk_page_end
        nonlocal chunk_index

        if not current_blocks:
            return

        text = "\n\n".join(
            current_blocks
        ).strip()

        if not text:
            return

        chunk = {
            "chunk_id": make_chunk_id(
                source_path,
                chunk_index,
                text
            ),

            "document_id": page_records[0].get(
                "sha256"
            ),

            "source_path": source_path,

            "page_start": chunk_page_start,

            "page_end": chunk_page_end,

            "chunk_index": chunk_index,

            "text": text,

            "word_count": word_count(text),

            "char_count": len(text),

            "content_hash": make_content_hash(
                text
            )
        }

        # Preserve useful metadata if present.
        for key in [
            "top_level_folder",
            "classification",
            "profile",
            "duplicate_count"
        ]:

            if key in page_records[0]:
                chunk[key] = page_records[0][key]

        chunks.append(chunk)

        chunk_index += 1

        # ----------------------------------------------------
        # OVERLAP
        # ----------------------------------------------------

        words = text.split()

        overlap = words[-OVERLAP_WORDS:]

        if overlap:

            current_blocks = [
                " ".join(overlap)
            ]

            current_words = len(overlap)

        else:

            current_blocks = []
            current_words = 0

        # The overlap belongs to the end page.
        chunk_page_start = chunk_page_end

    # ========================================================
    # PROCESS PAGES
    # ========================================================

    for page in page_records:

        page_number = page.get("page")

        try:
            page_number = int(page_number)
        except (TypeError, ValueError):
            continue

        page_text = normalize_text(
            page.get("text", "")
        )

        if not page_text:
            continue

        blocks = split_paragraphs(
            page_text
        )

        # Split oversized paragraphs.
        expanded_blocks = []

        for block in blocks:

            expanded_blocks.extend(
                split_long_text(block)
            )

        for block in expanded_blocks:

            block_words = word_count(block)

            if block_words == 0:
                continue

            # ------------------------------------------------
            # Start a new chunk
            # ------------------------------------------------

            if chunk_page_start is None:

                chunk_page_start = page_number

            # ------------------------------------------------
            # Calculate page span
            # ------------------------------------------------

            page_span = (
                page_number
                - chunk_page_start
                + 1
            )

            # ------------------------------------------------
            # Decide whether to flush
            # ------------------------------------------------

            should_flush = (
                current_blocks
                and (
                    current_words + block_words
                    > MAX_WORDS

                    or

                    page_span
                    > MAX_PAGES_PER_CHUNK
                )
            )

            if should_flush:

                flush_chunk()

                # Start new chunk at this page.
                chunk_page_start = page_number

                # Remove overlap if the overlap itself
                # would cause the new chunk to exceed
                # the page limit.
                current_page_span = (
                    page_number
                    - chunk_page_start
                    + 1
                )

                if current_page_span > MAX_PAGES_PER_CHUNK:

                    current_blocks = []
                    current_words = 0

            # ------------------------------------------------
            # Add current block
            # ------------------------------------------------

            current_blocks.append(block)

            current_words += block_words

            chunk_page_end = page_number

            # ------------------------------------------------
            # Target reached
            # ------------------------------------------------

            if current_words >= TARGET_WORDS:

                flush_chunk()

    # ========================================================
    # FINAL CHUNK
    # ========================================================

    if current_blocks:

        flush_chunk()

    return chunks


# ============================================================
# MAIN
# ============================================================

def main():

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"Input file not found:\n"
            f"{INPUT_FILE}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print("=" * 60)
    print("B.Tech Brain - Corpus Chunker")
    print("=" * 60)

    print(f"Input : {INPUT_FILE}")
    print(f"Output: {OUTPUT_FILE}")
    print()

    # ========================================================
    # LOAD
    # ========================================================

    pages = load_pages()

    print(
        f"Loaded pages: {len(pages):,}"
    )

    # ========================================================
    # GROUP BY DOCUMENT
    # ========================================================

    documents = defaultdict(list)

    for page in pages:

        source_path = page.get(
            "source_path",
            ""
        )

        documents[source_path].append(
            page
        )

    # Sort pages within every document.
    for source_path in documents:

        documents[source_path].sort(
            key=lambda x: x.get(
                "page",
                0
            )
        )

    print(
        f"Documents: {len(documents):,}"
    )

    print()

    # ========================================================
    # CREATE CHUNKS
    # ========================================================

    total_chunks = 0
    total_chars = 0
    total_words = 0

    source_counter = Counter()
    chunk_sizes = Counter()
    duplicate_content = Counter()

    all_chunks = []

    document_number = 0

    for source_path, page_records in documents.items():

        document_number += 1

        chunks = chunk_document(
            page_records
        )

        for chunk in chunks:

            all_chunks.append(
                chunk
            )

            total_chunks += 1

            total_chars += chunk[
                "char_count"
            ]

            total_words += chunk[
                "word_count"
            ]

            duplicate_content[
                chunk["content_hash"]
            ] += 1

            # ----------------------------------------------
            # Chunk size bucket
            # ----------------------------------------------

            words = chunk[
                "word_count"
            ]

            if words < 300:

                bucket = "<300"

            elif words < 500:

                bucket = "300-499"

            elif words < 700:

                bucket = "500-699"

            elif words < 900:

                bucket = "700-899"

            elif words < 1100:

                bucket = "900-1099"

            else:

                bucket = "1100+"

            chunk_sizes[bucket] += 1

        # ----------------------------------------------
        # Top-level folder
        # ----------------------------------------------

        if "\\" in source_path:

            top_folder = source_path.split(
                "\\",
                1
            )[0]

        elif "/" in source_path:

            top_folder = source_path.split(
                "/",
                1
            )[0]

        else:

            top_folder = source_path

        source_counter[
            top_folder
        ] += len(chunks)

        if document_number % 50 == 0:

            print(
                f"Processed "
                f"{document_number:,}/"
                f"{len(documents):,} documents..."
            )

    # ========================================================
    # WRITE CHUNKS
    # ========================================================

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:

        for chunk in all_chunks:

            f.write(
                json.dumps(
                    chunk,
                    ensure_ascii=False
                )
                + "\n"
            )

    # ========================================================
    # DUPLICATE CONTENT
    # ========================================================

    duplicate_chunks = sum(
        count - 1
        for count in duplicate_content.values()
        if count > 1
    )

    # ========================================================
    # STATISTICS
    # ========================================================

    stats = {

        "input_pages":
            len(pages),

        "documents":
            len(documents),

        "chunks":
            total_chunks,

        "total_words":
            total_words,

        "total_characters":
            total_chars,

        "average_words_per_chunk":
            (
                total_words / total_chunks
                if total_chunks
                else 0
            ),

        "average_characters_per_chunk":
            (
                total_chars / total_chunks
                if total_chunks
                else 0
            ),

        "target_words":
            TARGET_WORDS,

        "max_words":
            MAX_WORDS,

        "overlap_words":
            OVERLAP_WORDS,

        "max_pages_per_chunk":
            MAX_PAGES_PER_CHUNK,

        "chunk_size_distribution":
            dict(chunk_sizes),

        "chunks_by_top_level_folder":
            dict(
                source_counter.most_common()
            ),

        "duplicate_content_chunks":
            duplicate_chunks
    }

    with STATS_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            stats,
            f,
            indent=2,
            ensure_ascii=False
        )

    # ========================================================
    # FINAL REPORT
    # ========================================================

    print()

    print("=" * 60)
    print("CHUNKING COMPLETE")
    print("=" * 60)

    print(
        f"Input pages       : "
        f"{len(pages):,}"
    )

    print(
        f"Documents         : "
        f"{len(documents):,}"
    )

    print(
        f"Chunks            : "
        f"{total_chunks:,}"
    )

    print(
        f"Total words       : "
        f"{total_words:,}"
    )

    print(
        f"Total characters  : "
        f"{total_chars:,}"
    )

    if total_chunks:

        print(
            f"Avg words/chunk   : "
            f"{total_words / total_chunks:.1f}"
        )

        print(
            f"Avg chars/chunk   : "
            f"{total_chars / total_chunks:.1f}"
        )

    print()

    print(
        "Chunk size distribution:"
    )

    for bucket in [
        "<300",
        "300-499",
        "500-699",
        "700-899",
        "900-1099",
        "1100+"
    ]:

        print(
            f"  {bucket:>8}: "
            f"{chunk_sizes.get(bucket, 0):,}"
        )

    print()

    print(
        f"Max pages/chunk  : "
        f"{MAX_PAGES_PER_CHUNK}"
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )

    print(
        f"Stats : {STATS_FILE}"
    )

    print()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()