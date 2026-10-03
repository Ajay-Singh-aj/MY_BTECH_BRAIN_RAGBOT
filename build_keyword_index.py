import json
import pickle
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

CHUNKS_FILE = BASE_DIR / "processed" / "chunks" / "chunks.jsonl"
OUTPUT_DIR = BASE_DIR / "processed" / "keyword_index"

VECTORIZER_FILE = OUTPUT_DIR / "tfidf_vectorizer.pkl"
MATRIX_FILE = OUTPUT_DIR / "tfidf_matrix.pkl"
METADATA_FILE = OUTPUT_DIR / "metadata.jsonl"


# ============================================================
# LOAD CHUNKS
# ============================================================

print("=" * 65)
print("Building keyword retrieval index")
print("=" * 65)

print("\nLoading chunks...")

records = []

with CHUNKS_FILE.open("r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()

        if not line:
            continue

        record = json.loads(line)
        records.append(record)

print(f"Chunks loaded: {len(records):,}")


# ============================================================
# EXTRACT TEXT
# ============================================================

texts = []

for record in records:
    text = record.get("text", "")

    if not isinstance(text, str):
        text = str(text)

    texts.append(text)


# ============================================================
# BUILD TF-IDF
# ============================================================

print("\nBuilding TF-IDF index...")

vectorizer = TfidfVectorizer(
    lowercase=True,
    strip_accents="unicode",

    # Word n-grams help technical phrases:
    # "heat transfer", "mass transfer", "gradient descent", etc.
    ngram_range=(1, 2),

    min_df=2,
    max_df=0.98,

    # Avoid an unnecessarily huge vocabulary.
    max_features=300_000,

    sublinear_tf=True,
)

tfidf_matrix = vectorizer.fit_transform(texts)

print(f"Matrix shape: {tfidf_matrix.shape}")
print(f"Vocabulary size: {len(vectorizer.vocabulary_):,}")


# ============================================================
# SAVE
# ============================================================

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("\nSaving index...")

with VECTORIZER_FILE.open("wb") as f:
    pickle.dump(vectorizer, f)

with MATRIX_FILE.open("wb") as f:
    pickle.dump(tfidf_matrix, f)


# Save metadata in exactly the same order as the TF-IDF matrix.
with METADATA_FILE.open("w", encoding="utf-8") as f:
    for record in records:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


print("\n" + "=" * 65)
print("KEYWORD INDEX COMPLETE")
print("=" * 65)

print(f"Vectorizer : {VECTORIZER_FILE}")
print(f"Matrix     : {MATRIX_FILE}")
print(f"Metadata   : {METADATA_FILE}")
print(f"Documents  : {len(records):,}")
print(f"Features   : {len(vectorizer.vocabulary_):,}")