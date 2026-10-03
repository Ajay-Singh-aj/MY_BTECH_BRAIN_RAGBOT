import json
from pathlib import Path

FILE = Path("processed/chunks/chunks.jsonl")

required = [
    "chunk_id",
    "document_id",
    "source_path",
    "page_start",
    "page_end",
    "chunk_index",
    "text",
    "word_count",
    "char_count",
    "content_hash",
]

total = 0
bad = 0
json_errors = 0

with FILE.open("r", encoding="utf-8") as f:

    for line_number, line in enumerate(f, 1):

        line = line.strip()

        if not line:
            continue

        total += 1

        try:
            record = json.loads(line)

        except json.JSONDecodeError as e:
            print(f"JSON ERROR at line {line_number}: {e}")
            json_errors += 1
            continue

        missing = [
            key for key in required
            if key not in record
        ]

        if missing:
            print(
                f"BAD RECORD at line {line_number}: "
                f"missing {missing}"
            )
            bad += 1
            continue

        if not record["text"].strip():
            print(
                f"BAD RECORD at line {line_number}: empty text"
            )
            bad += 1

print()
print("=" * 50)
print("CHUNK VALIDATION")
print("=" * 50)
print(f"Records checked : {total:,}")
print(f"Bad records     : {bad:,}")
print(f"JSON errors     : {json_errors:,}")

if bad == 0 and json_errors == 0:
    print()
    print("STATUS: PASS")
else:
    print()
    print("STATUS: FAIL")
    