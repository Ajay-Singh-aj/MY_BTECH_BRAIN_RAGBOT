from pathlib import Path
import json
import sys


INPUT_FILE = Path("processed/pdf_pages.jsonl")

if len(sys.argv) < 2:
    print("Usage:")
    print('python inspect_document.py "3rd SEm\\ARTS201\\module 1 c.pdf"')
    sys.exit(1)

target = sys.argv[1]

records = []

with INPUT_FILE.open("r", encoding="utf-8") as f:
    for line in f:
        record = json.loads(line)

        if record["source_path"].lower() == target.lower():
            records.append(record)


if not records:
    print(f"Document not found: {target}")
    sys.exit(1)


print("=" * 80)
print(f"DOCUMENT: {target}")
print(f"PAGES: {len(records)}")
print("=" * 80)

for record in records:

    print()
    print("-" * 80)

    print(
        f"PAGE {record['page']} / {record['page_count']} | "
        f"status={record['page_status']} | "
        f"ocr={record['needs_ocr']} | "
        f"words={record['word_count']} | "
        f"chars={record['char_count']}"
    )

    text = record["text"].strip()

    if text:
        print()
        print(text[:600])
    else:
        print("[NO EXTRACTED TEXT]")


print()
print("=" * 80)