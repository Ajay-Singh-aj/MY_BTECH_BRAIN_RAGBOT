import json
from collections import Counter, defaultdict
from pathlib import Path


INPUT_FILE = Path("processed/clean/clean_pages.jsonl")


print("=" * 70)
print("CLEAN CORPUS DISTRIBUTION")
print("=" * 70)

if not INPUT_FILE.exists():
    raise SystemExit(f"File not found: {INPUT_FILE}")


# ---------------------------------------------------------
# Counters
# ---------------------------------------------------------

total_pages = 0
total_chars = 0

source_counts = Counter()
quality_counts = Counter()
category_counts = Counter()
classification_counts = Counter()

document_pages = Counter()
document_chars = Counter()

sha_to_paths = defaultdict(set)

page_counts = []

longest_pages = []
shortest_pages = []


# ---------------------------------------------------------
# Read corpus
# ---------------------------------------------------------

with INPUT_FILE.open("r", encoding="utf-8") as f:

    for line_number, line in enumerate(f, 1):

        line = line.strip()

        if not line:
            continue

        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            print(f"JSON error on line {line_number}: {exc}")
            continue

        total_pages += 1

        text = row.get("text", "") or ""
        chars = len(text)

        total_chars += chars

        source_counts[row.get("text_source", "missing")] += 1
        quality_counts[row.get("quality", "missing")] += 1

        category = row.get("source_category", "ROOT")
        category_counts[category] += 1

        classification = row.get(
            "document_classification",
            "unknown"
        )
        classification_counts[classification] += 1

        source_path = row.get("source_path", "UNKNOWN")

        document_pages[source_path] += 1
        document_chars[source_path] += chars

        sha = row.get("sha256")

        if sha:
            sha_to_paths[sha].add(source_path)

        page_counts.append(chars)


# ---------------------------------------------------------
# Basic statistics
# ---------------------------------------------------------

print()
print("BASIC SIZE")
print("-" * 70)

print(f"Pages:                  {total_pages:,}")
print(f"Characters:             {total_chars:,}")

if total_pages:
    print(
        f"Average chars/page:     "
        f"{total_chars / total_pages:,.1f}"
    )


# ---------------------------------------------------------
# Text source
# ---------------------------------------------------------

print()
print("TEXT SOURCE")
print("-" * 70)

for key, value in source_counts.most_common():
    print(f"{key:25} {value:>8,}")


# ---------------------------------------------------------
# Quality
# ---------------------------------------------------------

print()
print("QUALITY")
print("-" * 70)

for key, value in quality_counts.most_common():
    print(f"{key:25} {value:>8,}")


# ---------------------------------------------------------
# Top-level folders
# ---------------------------------------------------------

print()
print("TOP-LEVEL SOURCE CATEGORIES")
print("-" * 70)

for key, value in category_counts.most_common():
    print(f"{key:35} {value:>8,}")


# ---------------------------------------------------------
# Document classifications
# ---------------------------------------------------------

print()
print("DOCUMENT CLASSIFICATION")
print("-" * 70)

for key, value in classification_counts.most_common():
    print(f"{str(key):25} {value:>8,}")


# ---------------------------------------------------------
# Document count
# ---------------------------------------------------------

print()
print("DOCUMENTS")
print("-" * 70)

print(f"Unique source files:     {len(document_pages):,}")


# ---------------------------------------------------------
# Largest documents by page count
# ---------------------------------------------------------

print()
print("LARGEST DOCUMENTS BY PAGE COUNT")
print("-" * 70)

for path, pages in document_pages.most_common(30):

    print(
        f"{pages:>5} pages | "
        f"{document_chars[path]:>12,} chars | "
        f"{path}"
    )


# ---------------------------------------------------------
# Largest documents by characters
# ---------------------------------------------------------

print()
print("LARGEST DOCUMENTS BY CHARACTER COUNT")
print("-" * 70)

for path, chars in sorted(
    document_chars.items(),
    key=lambda x: x[1],
    reverse=True
)[:30]:

    print(
        f"{chars:>12,} chars | "
        f"{document_pages[path]:>5} pages | "
        f"{path}"
    )


# ---------------------------------------------------------
# Duplicate SHA groups
# ---------------------------------------------------------

duplicate_groups = []

for sha, paths in sha_to_paths.items():

    if len(paths) > 1:
        duplicate_groups.append(
            (sha, sorted(paths))
        )


print()
print("DUPLICATE SHA-256 GROUPS")
print("-" * 70)

print(
    f"Duplicate groups:       "
    f"{len(duplicate_groups):,}"
)

duplicate_file_count = sum(
    len(paths)
    for _, paths in duplicate_groups
)

print(
    f"Files involved:         "
    f"{duplicate_file_count:,}"
)

for sha, paths in duplicate_groups[:20]:

    print()
    print(f"SHA256: {sha}")

    for path in paths:
        print(f"  {path}")


# ---------------------------------------------------------
# Page-size distribution
# ---------------------------------------------------------

print()
print("PAGE TEXT LENGTH DISTRIBUTION")
print("-" * 70)

bins = [
    (0, 99),
    (100, 499),
    (500, 999),
    (1000, 1999),
    (2000, 4999),
    (5000, 9999),
    (10000, 19999),
    (20000, float("inf")),
]

for low, high in bins:

    count = sum(
        1
        for chars in page_counts
        if low <= chars <= high
    )

    if high == float("inf"):
        label = f"{low:,}+"
    else:
        label = f"{low:,}-{high:,}"

    print(f"{label:15} {count:>8,}")


# ---------------------------------------------------------
# Very short pages
# ---------------------------------------------------------

short_pages = []

with INPUT_FILE.open("r", encoding="utf-8") as f:

    for line in f:

        line = line.strip()

        if not line:
            continue

        row = json.loads(line)

        text = row.get("text", "") or ""

        if 1 <= len(text) < 100:

            short_pages.append(
                (
                    len(text),
                    row.get("source_path"),
                    row.get("page"),
                    text
                )
            )


print()
print("SHORT ACCEPTED PAGES (<100 CHARACTERS)")
print("-" * 70)

print(f"Count: {len(short_pages):,}")

for chars, path, page, text in short_pages[:30]:

    print()
    print(f"{chars} chars | {path} | page {page}")
    print(repr(text))


print()
print("=" * 70)
print("INSPECTION COMPLETE")
print("=" * 70)