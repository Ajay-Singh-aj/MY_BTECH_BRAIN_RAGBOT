import os
import json
import pickle
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from google import genai


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

FAISS_INDEX_FILE = (
    BASE_DIR / "processed" / "embeddings" / "index.faiss"
)

FAISS_METADATA_FILE = (
    BASE_DIR / "processed" / "embeddings" / "metadata.jsonl"
)

KEYWORD_DIR = BASE_DIR / "processed" / "keyword_index"

TFIDF_VECTORIZER_FILE = (
    KEYWORD_DIR / "tfidf_vectorizer.pkl"
)

TFIDF_MATRIX_FILE = (
    KEYWORD_DIR / "tfidf_matrix.pkl"
)

KEYWORD_METADATA_FILE = (
    KEYWORD_DIR / "metadata.jsonl"
)


# ============================================================
# MODELS
# ============================================================

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Current Gemini model used by your working setup.
GEMINI_MODEL = "gemini-3.8-flash"


# ============================================================
# RETRIEVAL SETTINGS
# ============================================================

# Retrieve a larger candidate pool first.
FAISS_CANDIDATES = 20
KEYWORD_CANDIDATES = 20

# Final number of chunks given to Gemini.
FINAL_TOP_K = 8

# Relative importance of semantic vs keyword retrieval.
VECTOR_WEIGHT = 0.65
KEYWORD_WEIGHT = 0.35

# Maximum context sent to Gemini.
MAX_CONTEXT_CHARS = 24000


# ============================================================
# GEMINI
# ============================================================

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY environment variable not found.\n"
        "Set it in PowerShell before running the program."
    )

client = genai.Client(api_key=API_KEY)


# ============================================================
# LOAD FAISS
# ============================================================

print("=" * 65)
print("B.Tech Brain - Hybrid RAG")
print("=" * 65)

print("\nLoading FAISS index...")

faiss_index = faiss.read_index(str(FAISS_INDEX_FILE))

print(f"Vectors: {faiss_index.ntotal:,}")


# ============================================================
# LOAD FAISS METADATA
# ============================================================

print("Loading FAISS metadata...")

faiss_metadata = []

with FAISS_METADATA_FILE.open("r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()

        if line:
            faiss_metadata.append(json.loads(line))

print(f"Metadata records: {len(faiss_metadata):,}")


if len(faiss_metadata) != faiss_index.ntotal:
    raise RuntimeError(
        "FAISS index and metadata have different sizes."
    )


# ============================================================
# LOAD EMBEDDING MODEL
# ============================================================

print("\nLoading embedding model...")

embedding_model = SentenceTransformer(EMBEDDING_MODEL)

print("Embedding model ready.")


# ============================================================
# LOAD TF-IDF
# ============================================================

print("\nLoading keyword retrieval index...")

with TFIDF_VECTORIZER_FILE.open("rb") as f:
    tfidf_vectorizer = pickle.load(f)

with TFIDF_MATRIX_FILE.open("rb") as f:
    tfidf_matrix = pickle.load(f)

keyword_metadata = []

with KEYWORD_METADATA_FILE.open("r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()

        if line:
            keyword_metadata.append(json.loads(line))

print(f"Keyword records: {len(keyword_metadata):,}")
print(f"Keyword matrix: {tfidf_matrix.shape}")


if len(keyword_metadata) != tfidf_matrix.shape[0]:
    raise RuntimeError(
        "TF-IDF matrix and metadata have different sizes."
    )


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_text(record):
    text = record.get("text", "")

    if not isinstance(text, str):
        text = str(text)

    return text


def get_source(record):
    return (
        record.get("source_file")
        or record.get("source")
        or record.get("file")
        or record.get("path")
        or "Unknown source"
    )


def get_page_start(record):
    return (
        record.get("page_start")
        or record.get("page")
        or record.get("page_number")
        or "?"
    )


def get_page_end(record):
    return (
        record.get("page_end")
        or record.get("page")
        or record.get("page_number")
        or get_page_start(record)
    )


def get_chunk_id(record):
    return record.get("chunk_id", "?")


def normalize_scores(scores):
    """
    Min-max normalize scores into approximately 0-1.
    """
    scores = np.asarray(scores, dtype=np.float32)

    if len(scores) == 0:
        return scores

    min_score = scores.min()
    max_score = scores.max()

    if max_score - min_score < 1e-8:
        return np.ones_like(scores)

    return (scores - min_score) / (max_score - min_score)


# ============================================================
# HYBRID RETRIEVAL
# ============================================================

def hybrid_search(query):
    """
    Perform:
      1. FAISS semantic retrieval
      2. TF-IDF keyword retrieval
      3. Score fusion
      4. Duplicate suppression
      5. Final ranking
    """

    # --------------------------------------------------------
    # 1. SEMANTIC SEARCH
    # --------------------------------------------------------

    query_embedding = embedding_model.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype("float32")

    vector_scores, vector_ids = faiss_index.search(
        query_embedding,
        FAISS_CANDIDATES,
    )

    vector_scores = vector_scores[0]
    vector_ids = vector_ids[0]

    vector_candidates = []

    for score, idx in zip(vector_scores, vector_ids):

        if idx < 0:
            continue

        vector_candidates.append(
            {
                "index": int(idx),
                "vector_score": float(score),
            }
        )

    # --------------------------------------------------------
    # 2. KEYWORD SEARCH
    # --------------------------------------------------------

    query_tfidf = tfidf_vectorizer.transform([query])

    keyword_scores_all = cosine_similarity(
        query_tfidf,
        tfidf_matrix,
    )[0]

    keyword_top_indices = np.argsort(
        keyword_scores_all
    )[::-1][:KEYWORD_CANDIDATES]

    keyword_candidates = []

    for idx in keyword_top_indices:

        score = float(keyword_scores_all[idx])

        if score <= 0:
            continue

        keyword_candidates.append(
            {
                "index": int(idx),
                "keyword_score": score,
            }
        )

    # --------------------------------------------------------
    # 3. COLLECT ALL CANDIDATES
    # --------------------------------------------------------

    candidates = {}

    for item in vector_candidates:

        idx = item["index"]

        candidates.setdefault(
            idx,
            {
                "index": idx,
                "vector_score": 0.0,
                "keyword_score": 0.0,
            },
        )

        candidates[idx]["vector_score"] = item["vector_score"]

    for item in keyword_candidates:

        idx = item["index"]

        candidates.setdefault(
            idx,
            {
                "index": idx,
                "vector_score": 0.0,
                "keyword_score": 0.0,
            },
        )

        candidates[idx]["keyword_score"] = item["keyword_score"]

    candidates = list(candidates.values())

    # --------------------------------------------------------
    # 4. NORMALIZE SCORES
    # --------------------------------------------------------

    vector_raw = np.array(
        [x["vector_score"] for x in candidates],
        dtype=np.float32,
    )

    keyword_raw = np.array(
        [x["keyword_score"] for x in candidates],
        dtype=np.float32,
    )

    vector_norm = normalize_scores(vector_raw)
    keyword_norm = normalize_scores(keyword_raw)

    # --------------------------------------------------------
    # 5. HYBRID SCORE
    # --------------------------------------------------------

    for i, candidate in enumerate(candidates):

        candidate["vector_normalized"] = float(vector_norm[i])
        candidate["keyword_normalized"] = float(keyword_norm[i])

        candidate["hybrid_score"] = (
            VECTOR_WEIGHT * vector_norm[i]
            + KEYWORD_WEIGHT * keyword_norm[i]
        )

    candidates.sort(
        key=lambda x: x["hybrid_score"],
        reverse=True,
    )

    # --------------------------------------------------------
    # 6. BUILD RESULTS
    # --------------------------------------------------------

    results = []

    seen_content = set()

    for candidate in candidates:

        idx = candidate["index"]

        record = faiss_metadata[idx]

        text = get_text(record)

        # Prevent exact duplicate text from occupying
        # multiple final positions.
        normalized_text = " ".join(
            text.lower().split()
        )

        if normalized_text in seen_content:
            continue

        seen_content.add(normalized_text)

        result = dict(record)

        result["_vector_score"] = candidate["vector_score"]
        result["_keyword_score"] = candidate["keyword_score"]
        result["_hybrid_score"] = candidate["hybrid_score"]

        results.append(result)

        if len(results) >= FINAL_TOP_K:
            break

    return results


# ============================================================
# CONTEXT BUILDER
# ============================================================

def build_context(results):

    context_parts = []
    current_chars = 0

    for i, record in enumerate(results, start=1):

        source = get_source(record)
        page_start = get_page_start(record)
        page_end = get_page_end(record)
        text = get_text(record)

        block = (
            f"\n--- SOURCE {i} ---\n"
            f"File: {source}\n"
            f"Pages: {page_start}-{page_end}\n"
            f"Text:\n{text}\n"
        )

        if current_chars + len(block) > MAX_CONTEXT_CHARS:
            break

        context_parts.append(block)
        current_chars += len(block)

    return "\n".join(context_parts)


# ============================================================
# GEMINI ANSWER
# ============================================================

def generate_answer(user_question, results):

    context = build_context(results)

    system_instruction = """
You are the B.Tech Brain assistant.

Answer the user's question using the retrieved knowledge-base
material provided below.

Rules:

1. Ground the answer in the retrieved material.
2. Do not invent information that is absent from the retrieved
   material.
3. If the retrieved material is insufficient, explicitly say so.
4. For technical questions, explain equations and terminology
   clearly.
5. Prefer a direct answer before additional explanation.
6. Cite the relevant source numbers such as [SOURCE 1].
7. Do not claim that a source says something unless it actually
   appears in the supplied text.
"""

    prompt = f"""
USER QUESTION:
{user_question}

RETRIEVED KNOWLEDGE BASE:
{context}

Provide the best grounded answer possible.
"""

    interaction = client.interactions.create(
        model=GEMINI_MODEL,
        system_instruction=system_instruction,
        input=prompt,
        generation_config={
            "thinking_level": "low"
        },
    )

    return interaction.output_text


# ============================================================
# PRINT SOURCES
# ============================================================

def print_sources(results):

    print("\n### Sources")

    for i, record in enumerate(results, start=1):

        source = get_source(record)
        page_start = get_page_start(record)
        page_end = get_page_end(record)

        vector_score = record.get("_vector_score", 0.0)
        keyword_score = record.get("_keyword_score", 0.0)
        hybrid_score = record.get("_hybrid_score", 0.0)

        print(
            f"{i}. {source}"
        )

        print(
            f"   Pages: {page_start}-{page_end}"
        )

        print(
            f"   Hybrid: {hybrid_score:.4f} | "
            f"Vector: {vector_score:.4f} | "
            f"Keyword: {keyword_score:.4f}"
        )


# ============================================================
# MAIN CHAT LOOP
# ============================================================

print("\nGemini client ready.")

print("\n" + "=" * 65)
print("B.Tech Brain is ready.")
print("Type 'exit' to quit.")
print("=" * 65)


while True:

    try:
        user_input = input("\nYou > ").strip()

    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")
        break

    if not user_input:
        continue

    if user_input.lower() in {
        "exit",
        "quit",
    }:
        print("Goodbye.")
        break

    print("\nSearching your B.Tech knowledge base...")

    try:

        results = hybrid_search(user_input)

        if not results:
            print("No relevant material found.")
            continue

        print("Generating answer...")

        answer = generate_answer(
            user_input,
            results,
        )

        print("\n" + "=" * 65)
        print("ANSWER")
        print("=" * 65)

        print(answer)

        print_sources(results)

        print("\n" + "-" * 65)

    except Exception as e:

        print("\nERROR:")
        print(type(e).__name__)
        print(str(e))