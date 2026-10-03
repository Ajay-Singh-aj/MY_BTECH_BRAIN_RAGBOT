import json
from collections import Counter, defaultdict
from pathlib import Path

OCR_FILE = Path("processed/ocr/pdf_pages_ocr.jsonl")
ERROR_FILE = Path("processed/ocr/ocr_errors.jsonl")


def load_jsonl(path):
    if not path.exists():
        print(f"FILE NOT FOUND: {path}")
        return []

    rows = []

    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()

            if not line:
                continue

            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"JSON ERROR in {path}, line {line_no}: {e}")

    return rows


print("=" * 70)
print("OCR OUTPUT INSPECTION")
print("=" * 70)

# ---------------------------------------------------------
# Load OCR output
# ---------------------------------------------------------

rows = load_jsonl(OCR_FILE)

print(f"\nOCR records loaded: {len(rows):,}")

if not rows:
    raise SystemExit("No OCR records found.")

# ---------------------------------------------------------
# Basic counts
# ---------------------------------------------------------

text_source_counts = Counter(
    row.get("text_source", "missing")
    for row in rows
)

ocr_used_counts = Counter(
    row.get("ocr_used", False)
    for row in rows
)

print("\nTEXT SOURCE")
print("-" * 70)

for key, count in text_source_counts.items():
    print(f"{key:15} {count:>8,}")

print("\nOCR USED")
print("-" * 70)

for key, count in ocr_used_counts.items():
    print(f"{str(key):15} {count:>8,}")

# ---------------------------------------------------------
# Empty OCR pages
# ---------------------------------------------------------

empty_ocr = [
    row for row in rows
    if row.get("ocr_used") is True
    and not (row.get("ocr_text") or "").strip()
]

print("\nEMPTY OCR PAGES")
print("-" * 70)
print(f"Count: {len(empty_ocr):,}")

# Group by PDF
empty_by_file = defaultdict(list)

for row in empty_ocr:
    empty_by_file[row.get("source_path", "UNKNOWN")].append(
        row.get("page")
    )

print(f"PDFs containing empty OCR pages: {len(empty_by_file):,}")

print("\nTop PDFs by empty OCR pages:")
print("-" * 70)

for path, pages in sorted(
    empty_by_file.items(),
    key=lambda x: len(x[1]),
    reverse=True
)[:30]:

    print(f"{len(pages):>4} pages | {path}")

    if len(pages) <= 20:
        print(f"             pages: {pages}")

# ---------------------------------------------------------
# OCR errors inside page records
# ---------------------------------------------------------

record_errors = [
    row for row in rows
    if row.get("ocr_error")
]

print("\nERRORS STORED IN OCR RECORDS")
print("-" * 70)
print(f"Count: {len(record_errors):,}")

for row in record_errors[:20]:
    print()
    print("File :", row.get("source_path"))
    print("Page :", row.get("page"))
    print("Error:", row.get("ocr_error"))

# ---------------------------------------------------------
# Separate error file
# ---------------------------------------------------------

errors = load_jsonl(ERROR_FILE)

print("\nSEPARATE ERROR FILE")
print("-" * 70)
print(f"Error records: {len(errors):,}")

for error in errors[:20]:
    print()
    print(json.dumps(error, indent=2, ensure_ascii=False))

# ---------------------------------------------------------
# Native / OCR character statistics
# ---------------------------------------------------------

native_chars = [
    row.get("native_char_count", 0)
    for row in rows
]

ocr_chars = [
    row.get("ocr_char_count", 0)
    for row in rows
]

print("\nCHARACTER STATISTICS")
print("-" * 70)

print(f"Native characters: {sum(native_chars):,}")
print(f"OCR characters:    {sum(ocr_chars):,}")

# ---------------------------------------------------------
# OCR pages with very little text
# ---------------------------------------------------------

short_ocr = [
    row for row in rows
    if row.get("ocr_used") is True
    and 0 < row.get("ocr_char_count", 0) < 20
]

print("\nSHORT OCR RESULTS")
print("-" * 70)
print(f"OCR pages with 1-19 characters: {len(short_ocr):,}")

for row in short_ocr[:30]:
    print()
    print("File :", row.get("source_path"))
    print("Page :", row.get("page"))
    print("Text :", repr(row.get("ocr_text")))

print("\n" + "=" * 70)
print("INSPECTION COMPLETE")
print("=" * 70)