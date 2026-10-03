import json
from pathlib import Path

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer


# ============================================================
# CONFIG
# ============================================================

INPUT_FILE = Path(
    "processed/chunks/chunks.jsonl"
)

OUTPUT_DIR = Path(
    "processed/embeddings"
)

INDEX_FILE = OUTPUT_DIR / "index.faiss"
METADATA_FILE = OUTPUT_DIR / "metadata.jsonl"
STATS_FILE = OUTPUT_DIR / "embedding_stats.json"

# Good general-purpose retrieval model.
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Batch size. Lower this if RAM becomes a problem.
BATCH_SIZE = 32


# ============================================================
# LOAD CHUNKS
# ============================================================

def load_chunks():

    chunks = []

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

            except json.JSONDecodeError as e:

                print(
                    f"WARNING: invalid JSON "
                    f"at line {line_number}: {e}"
                )

                continue

            text = record.get(
                "text",
                ""
            ).strip()

            if not text:
                continue

            chunks.append(record)

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
    print("B.Tech Brain - Embedding Pipeline")
    print("=" * 60)

    print()
    print(
        f"Model: {MODEL_NAME}"
    )

    print(
        f"Input: {INPUT_FILE}"
    )

    print()

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    chunks = load_chunks()

    print(
        f"Chunks loaded: {len(chunks):,}"
    )

    if not chunks:
        raise RuntimeError(
            "No chunks found."
        )

    # --------------------------------------------------------
    # Prepare texts
    # --------------------------------------------------------

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    # --------------------------------------------------------
    # Load embedding model
    # --------------------------------------------------------

    print()
    print("Loading embedding model...")
    print(
        "The first run may download the model."
    )
    print()

    model = SentenceTransformer(
        MODEL_NAME
    )

    print(
        f"Embedding dimension: "
        f"{model.get_sentence_embedding_dimension()}"
    )

    # --------------------------------------------------------
    # Generate embeddings
    # --------------------------------------------------------

    print()
    print("Generating embeddings...")
    print()

    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    # --------------------------------------------------------
    # Convert to float32 for FAISS
    # --------------------------------------------------------

    embeddings = np.asarray(
        embeddings,
        dtype="float32"
    )

    print()
    print(
        f"Embedding matrix: "
        f"{embeddings.shape}"
    )

    # --------------------------------------------------------
    # Build FAISS index
    # --------------------------------------------------------

    print()
    print("Building FAISS index...")

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatIP(
        dimension
    )

    index.add(
        embeddings
    )

    print(
        f"FAISS vectors: "
        f"{index.ntotal:,}"
    )

    # --------------------------------------------------------
    # Save FAISS index
    # --------------------------------------------------------

    faiss.write_index(
        index,
        str(INDEX_FILE)
    )

    # --------------------------------------------------------
    # Save metadata
    # --------------------------------------------------------

    print(
        "Saving metadata..."
    )

    with METADATA_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:

        for chunk in chunks:

            # Keep metadata separate from
            # the embedding matrix.
            metadata = {
                "chunk_id": chunk.get(
                    "chunk_id"
                ),
                "document_id": chunk.get(
                    "document_id"
                ),
                "source_path": chunk.get(
                    "source_path"
                ),
                "page_start": chunk.get(
                    "page_start"
                ),
                "page_end": chunk.get(
                    "page_end"
                ),
                "chunk_index": chunk.get(
                    "chunk_index"
                ),
                "word_count": chunk.get(
                    "word_count"
                ),
                "char_count": chunk.get(
                    "char_count"
                ),
                "content_hash": chunk.get(
                    "content_hash"
                ),
                "text": chunk.get(
                    "text"
                )
            }

            f.write(
                json.dumps(
                    metadata,
                    ensure_ascii=False
                )
                + "\n"
            )

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    stats = {
        "model": MODEL_NAME,
        "chunks": len(chunks),
        "embedding_dimension": dimension,
        "index_type": "IndexFlatIP",
        "normalized_embeddings": True,
        "batch_size": BATCH_SIZE,
        "index_file": str(INDEX_FILE),
        "metadata_file": str(METADATA_FILE)
    }

    with STATS_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            stats,
            f,
            indent=2
        )

    # --------------------------------------------------------
    # Final report
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("EMBEDDING PIPELINE COMPLETE")
    print("=" * 60)

    print(
        f"Chunks embedded    : "
        f"{len(chunks):,}"
    )

    print(
        f"Vector dimension   : "
        f"{dimension}"
    )

    print(
        f"FAISS vectors      : "
        f"{index.ntotal:,}"
    )

    print()
    print(
        f"Index    : {INDEX_FILE}"
    )

    print(
        f"Metadata : {METADATA_FILE}"
    )

    print(
        f"Stats    : {STATS_FILE}"
    )

    print()


if __name__ == "__main__":
    main()