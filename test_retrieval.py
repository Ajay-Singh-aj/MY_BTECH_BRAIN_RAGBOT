import json
from pathlib import Path

import faiss
from sentence_transformers import SentenceTransformer


# ============================================================
# CONFIG
# ============================================================

INDEX_FILE = Path(
    "processed/embeddings/index.faiss"
)

METADATA_FILE = Path(
    "processed/embeddings/metadata.jsonl"
)

MODEL_NAME = (
    "sentence-transformers/all-MiniLM-L6-v2"
)

TOP_K = 5


# ============================================================
# LOAD
# ============================================================

print("=" * 60)
print("B.Tech Brain - Retrieval Test")
print("=" * 60)

print("\nLoading FAISS index...")

index = faiss.read_index(
    str(INDEX_FILE)
)

print(
    f"Vectors loaded: {index.ntotal:,}"
)

print("\nLoading metadata...")

metadata = []

with METADATA_FILE.open(
    "r",
    encoding="utf-8"
) as f:

    for line in f:
        line = line.strip()

        if line:
            metadata.append(
                json.loads(line)
            )

print(
    f"Metadata records: {len(metadata):,}"
)

if index.ntotal != len(metadata):

    raise RuntimeError(
        "FAISS index and metadata count do not match."
    )

print("\nLoading embedding model...")

model = SentenceTransformer(
    MODEL_NAME
)

print("Ready.")


# ============================================================
# SEARCH
# ============================================================

def search(query, top_k=TOP_K):

    query_embedding = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    scores, indices = index.search(
        query_embedding,
        top_k
    )

    print("\n")
    print("=" * 60)
    print(f"QUERY: {query}")
    print("=" * 60)

    for rank, (score, idx) in enumerate(
        zip(scores[0], indices[0]),
        1
    ):

        if idx < 0:
            continue

        item = metadata[idx]

        print()
        print("-" * 60)
        print(f"RESULT #{rank}")
        print("-" * 60)

        print(
            f"Score      : {score:.4f}"
        )

        print(
            f"Source     : "
            f"{item.get('source_path')}"
        )

        print(
            f"Pages      : "
            f"{item.get('page_start')}"
            f"-"
            f"{item.get('page_end')}"
        )

        print(
            f"Chunk      : "
            f"{item.get('chunk_index')}"
        )

        print(
            f"Words      : "
            f"{item.get('word_count')}"
        )

        print("\nTEXT:\n")

        text = item.get(
            "text",
            ""
        )

        # Avoid flooding the terminal.
        if len(text) > 1800:
            print(
                text[:1800]
                + "\n...[truncated]"
            )
        else:
            print(text)


# ============================================================
# INTERACTIVE LOOP
# ============================================================

print()
print("=" * 60)
print("Ask questions about your B.Tech corpus.")
print("Type 'exit' to quit.")
print("=" * 60)

while True:

    try:
        query = input(
            "\nQuestion > "
        ).strip()

    except (KeyboardInterrupt, EOFError):

        print("\nExiting.")
        break

    if not query:
        continue

    if query.lower() in {
        "exit",
        "quit",
        "q"
    }:
        print("Exiting.")
        break

    search(query)