import json
import re
from collections import Counter
from pathlib import Path


INPUT_FILE = Path("processed/ocr/pdf_pages_ocr.jsonl")
OUTPUT_DIR = Path("processed/clean")

OUTPUT_FILE = OUTPUT_DIR / "clean_pages.jsonl"
REJECTED_FILE = OUTPUT_DIR / "rejected_pages.jsonl"
STATS_FILE = OUTPUT_DIR / "clean_corpus_stats.json"


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

# OCR shorter than this is usually not useful as standalone
# retrieval text. We keep it in the raw OCR file but do not
# put it into the clean corpus.
MIN_OCR_CHARS = 20

# Native extraction is trusted much more than OCR.
MIN_NATIVE_CHARS = 1

# Extremely short text consisting mostly of symbols/noise.
MIN_ALNUM_RATIO = 0.20


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def clean_whitespace(text):
    """Normalize whitespace while preserving the actual words."""
    if not text:
        return ""

    text = text.replace("\x00", " ")
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove excessive horizontal whitespace.
    text = re.sub(r"[ \t]+", " ", text)

    # Remove excessive blank lines.
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def alnum_ratio(text):
    """Fraction of characters that are letters/numbers."""
    if not text:
        return 0.0

    useful = sum(ch.isalnum() for ch in text)
    return useful / len(text)


def looks_like_noise(text):
    """
    Conservative noise detector.

    This is deliberately NOT used to reject native PDF text.
    It is mainly for OCR.
    """
    if not text:
        return True

    stripped = text.strip()

    if len(stripped) < MIN_OCR_CHARS:
        return True

    if alnum_ratio(stripped) < MIN_ALNUM_RATIO:
        return True

    # Lots of repeated single-character OCR garbage.
    words = stripped.split()

    if len(words) >= 5:
        single_char_words = sum(
            1 for word in words
            if len(re.sub(r"[^A-Za-z0-9]", "", word)) <= 1
        )

        if single_char_words / len(words) > 0.75:
            return True

    return False


def choose_text(row):
    """
    Decide which representation becomes the canonical text.

    Native text wins whenever it exists.

    OCR is used only when native text is empty and the OCR
    result passes conservative quality checks.
    """

    native = clean_whitespace(row.get("native_text", ""))
    ocr = clean_whitespace(row.get("ocr_text", ""))

    native_chars = len(native)

    # -----------------------------------------------------
    # Native text
    # -----------------------------------------------------

    if native_chars >= MIN_NATIVE_CHARS:
        return {
            "text": native,
            "text_source": "native",
            "quality": "native",
            "accepted": True,
            "reason": "native_text_available",
        }

    # -----------------------------------------------------
    # OCR
    # -----------------------------------------------------

    if not ocr:
        return {
            "text": "",
            "text_source": "none",
            "quality": "empty",
            "accepted": False,
            "reason": "no_native_or_ocr_text",
        }

    if looks_like_noise(ocr):
        return {
            "text": ocr,
            "text_source": "ocr",
            "quality": "ocr_rejected",
            "accepted": False,
            "reason": "ocr_too_short_or_noisy",
        }

    return {
        "text": ocr,
        "text_source": "ocr",
        "quality": "ocr_accepted",
        "accepted": True,
        "reason": "native_empty_ocr_usable",
    }


def source_category(source_path):
    """
    Derive the top-level corpus category from the source path.

    Example:
        CHE 311\\notes.pdf
        -> CHE 311
    """

    path = Path(source_path)

    parts = path.parts

    if len(parts) >= 2:
        return parts[0]

    return "ROOT"


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

print("=" * 70)
print("BUILDING CLEAN KNOWLEDGE CORPUS")
print("=" * 70)

if not INPUT_FILE.exists():
    raise SystemExit(
        f"\nInput file not found:\n{INPUT_FILE}\n"
        "Make sure the OCR pipeline has completed first."
    )

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Never modify the raw OCR file.
#
# We recreate only the derived clean files.

for path in [OUTPUT_FILE, REJECTED_FILE, STATS_FILE]:
    if path.exists():
        path.unlink()


stats = Counter()

source_categories = Counter()
quality_counts = Counter()
source_counts = Counter()

total_records = 0
accepted_records = 0
rejected_records = 0

native_pages = 0
ocr_pages = 0
empty_pages = 0

total_chars = 0


with INPUT_FILE.open("r", encoding="utf-8") as infile, \
     OUTPUT_FILE.open("w", encoding="utf-8") as clean_out, \
     REJECTED_FILE.open("w", encoding="utf-8") as rejected_out:

    for line_number, line in enumerate(infile, 1):

        line = line.strip()

        if not line:
            continue

        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            print(
                f"WARNING: malformed JSON on line {line_number}: {exc}"
            )
            stats["malformed_json"] += 1
            continue

        total_records += 1

        decision = choose_text(row)

        source_path = row.get("source_path", "")
        page = row.get("page")

        source_cat = source_category(source_path)

        source_categories[source_cat] += 1
        quality_counts[decision["quality"]] += 1
        source_counts[decision["text_source"]] += 1

        if decision["text_source"] == "native":
            native_pages += 1

        elif decision["text_source"] == "ocr":
            ocr_pages += 1

        else:
            empty_pages += 1

        # -------------------------------------------------
        # Base metadata
        # -------------------------------------------------

        clean_record = {
            # Identity
            "id": f"{source_path}::page_{page}",

            # Source
            "source_path": source_path,
            "file_name": row.get("file_name"),
            "source_folder": row.get("source_folder"),
            "source_category": source_cat,

            # Page
            "page": page,
            "page_count": row.get("page_count"),

            # Document identity
            "sha256": row.get("sha256"),
            "duplicate_count": row.get("duplicate_count"),
            "document_classification": row.get(
                "document_classification"
            ),

            # Canonical content
            "text": decision["text"],
            "text_source": decision["text_source"],
            "quality": decision["quality"],
            "quality_reason": decision["reason"],

            # OCR information
            "ocr_used": row.get("ocr_used", False),
            "ocr_dpi": row.get("ocr_dpi"),

            # Original extraction sizes
            "native_char_count": row.get(
                "native_char_count", 0
            ),
            "ocr_char_count": row.get(
                "ocr_char_count", 0
            ),
        }

        # -------------------------------------------------
        # Accepted page
        # -------------------------------------------------

        if decision["accepted"]:

            clean_out.write(
                json.dumps(
                    clean_record,
                    ensure_ascii=False
                ) + "\n"
            )

            accepted_records += 1
            total_chars += len(decision["text"])

        # -------------------------------------------------
        # Rejected page
        # -------------------------------------------------

        else:

            rejected_out.write(
                json.dumps(
                    clean_record,
                    ensure_ascii=False
                ) + "\n"
            )

            rejected_records += 1


# ---------------------------------------------------------
# Statistics
# ---------------------------------------------------------

stats_data = {
    "input_file": str(INPUT_FILE),
    "output_file": str(OUTPUT_FILE),
    "rejected_file": str(REJECTED_FILE),

    "total_records": total_records,
    "accepted_records": accepted_records,
    "rejected_records": rejected_records,

    "accepted_native_pages": native_pages,
    "accepted_ocr_pages": ocr_pages,

    "empty_or_rejected_pages": empty_pages,

    "total_accepted_characters": total_chars,

    "source_counts": dict(source_counts),
    "quality_counts": dict(quality_counts),
    "source_categories": dict(source_categories),

    "rules": {
        "min_ocr_chars": MIN_OCR_CHARS,
        "min_native_chars": MIN_NATIVE_CHARS,
        "min_alnum_ratio": MIN_ALNUM_RATIO,
        "native_text_priority": True,
        "ocr_noise_filter_enabled": True,
    },
}


with STATS_FILE.open("w", encoding="utf-8") as f:
    json.dump(
        stats_data,
        f,
        indent=2,
        ensure_ascii=False
    )


# ---------------------------------------------------------
# Report
# ---------------------------------------------------------

print()
print("=" * 70)
print("CLEAN CORPUS COMPLETE")
print("=" * 70)

print(f"Input records:             {total_records:,}")
print(f"Accepted records:          {accepted_records:,}")
print(f"Rejected records:          {rejected_records:,}")
print()
print(f"Accepted native pages:     {native_pages:,}")
print(f"Accepted OCR pages:        {ocr_pages:,}")
print(f"Empty/rejected pages:      {empty_pages:,}")
print()
print(f"Accepted characters:       {total_chars:,}")

print()
print("QUALITY")
print("-" * 70)

for key, value in quality_counts.most_common():
    print(f"{key:25} {value:>8,}")

print()
print("TEXT SOURCE")
print("-" * 70)

for key, value in source_counts.most_common():
    print(f"{key:25} {value:>8,}")

print()
print("OUTPUT")
print("-" * 70)

print(f"Clean corpus:              {OUTPUT_FILE}")
print(f"Rejected pages:            {REJECTED_FILE}")
print(f"Statistics:                {STATS_FILE}")

print()
print("=" * 70)
print("DONE")
print("=" * 70)