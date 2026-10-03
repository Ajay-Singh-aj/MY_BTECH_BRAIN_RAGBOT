from pathlib import Path
import csv
import json
import hashlib
import re
from pypdf import PdfReader


# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------

DATASET_ROOT = Path(r"C:\Users\ajay singh\Desktop\courses")
PROFILE_FILE = Path("document_profile.csv")

OUTPUT_DIR = Path("processed")
OUTPUT_FILE = OUTPUT_DIR / "pdf_pages.jsonl"
ERROR_FILE = OUTPUT_DIR / "extraction_errors.jsonl"

MIN_TEXT_CHARS = 50


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def normalize_text(text: str) -> str:
    """
    Conservative cleaning.
    We intentionally do NOT aggressively rewrite the text.
    """
    if not text:
        return ""

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove excessive spaces while preserving line structure
    text = re.sub(r"[ \t]+", " ", text)

    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def sha256_file(path: Path) -> str:
    """
    Calculate SHA-256 without loading the whole file into memory.
    """
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)

    return h.hexdigest()


def classify_page(text: str, document_classification: str) -> tuple[str, bool]:
    """
    Decide whether a page has usable extracted text.

    We keep this deliberately conservative.
    """
    char_count = len(text.strip())

    if char_count >= MIN_TEXT_CHARS:
        return "text_extracted", False

    if document_classification in {
        "needs_ocr",
        "mostly_scanned",
        "mixed"
    }:
        return "needs_ocr", True

    if char_count > 0:
        return "short_text", False

    return "needs_ocr", True


# ---------------------------------------------------------
# LOAD PROFILE
# ---------------------------------------------------------

if not PROFILE_FILE.exists():
    raise FileNotFoundError(
        f"Could not find {PROFILE_FILE}. "
        "Run document_profiler.py first."
    )

profiles = {}

with PROFILE_FILE.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)

    for row in reader:
        path_value = row.get("path", "").strip()

        if not path_value:
            continue

        profiles[path_value] = row


print(f"Loaded profile for {len(profiles)} PDFs.")


# ---------------------------------------------------------
# PREPARE OUTPUT
# ---------------------------------------------------------

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Start fresh
OUTPUT_FILE.write_text("", encoding="utf-8")
ERROR_FILE.write_text("", encoding="utf-8")


# ---------------------------------------------------------
# FIND PDFs
# ---------------------------------------------------------

pdf_files = sorted(DATASET_ROOT.rglob("*.pdf"))

print(f"Found {len(pdf_files)} PDF files.")
print()
print("Starting extraction...")
print()


# ---------------------------------------------------------
# PROCESS PDFs ONE AT A TIME
# ---------------------------------------------------------

processed = 0
successful = 0
failed = 0
pages_total = 0
pages_needing_ocr = 0


with OUTPUT_FILE.open("a", encoding="utf-8") as out_f, \
     ERROR_FILE.open("a", encoding="utf-8") as error_f:

    for pdf_path in pdf_files:

        processed += 1

        relative_path = pdf_path.relative_to(DATASET_ROOT)
        relative_path_str = str(relative_path)

        profile = profiles.get(relative_path_str, {})

        document_classification = profile.get(
            "classification",
            "unknown"
        )

        duplicate_count = int(
            profile.get("duplicate_count", "1") or "1"
        )

        try:
            reader = PdfReader(str(pdf_path))

            page_count = len(reader.pages)

            file_hash = profile.get("sha256", "")

            # Fallback in case hash isn't present in profile
            if not file_hash:
                file_hash = sha256_file(pdf_path)

            source_folder = (
                relative_path.parts[0]
                if len(relative_path.parts) > 1
                else ""
            )

            for page_number, page in enumerate(reader.pages, start=1):

                try:
                    raw_text = page.extract_text() or ""
                    text = normalize_text(raw_text)

                    page_status, needs_ocr = classify_page(
                        text,
                        document_classification
                    )

                    record = {
                        "source_path": relative_path_str,
                        "file_name": pdf_path.name,
                        "source_folder": source_folder,

                        "page": page_number,
                        "page_count": page_count,

                        "document_classification": document_classification,

                        "sha256": file_hash,
                        "duplicate_count": duplicate_count,

                        "page_status": page_status,
                        "needs_ocr": needs_ocr,

                        "text": text,

                        "char_count": len(text),
                        "word_count": len(text.split())
                    }

                    out_f.write(
                        json.dumps(
                            record,
                            ensure_ascii=False
                        ) + "\n"
                    )

                    pages_total += 1

                    if needs_ocr:
                        pages_needing_ocr += 1

                except Exception as page_error:

                    error_record = {
                        "source_path": relative_path_str,
                        "page": page_number,
                        "error": str(page_error)
                    }

                    error_f.write(
                        json.dumps(
                            error_record,
                            ensure_ascii=False
                        ) + "\n"
                    )

                    pages_total += 1
                    pages_needing_ocr += 1

            successful += 1

        except Exception as error:

            failed += 1

            error_record = {
                "source_path": relative_path_str,
                "error": str(error)
            }

            error_f.write(
                json.dumps(
                    error_record,
                    ensure_ascii=False
                ) + "\n"
            )

        # Progress
        if processed % 25 == 0 or processed == len(pdf_files):
            print(
                f"[{processed}/{len(pdf_files)}] "
                f"PDFs processed | "
                f"pages: {pages_total} | "
                f"OCR candidates: {pages_needing_ocr} | "
                f"errors: {failed}"
            )


# ---------------------------------------------------------
# FINAL REPORT
# ---------------------------------------------------------

print()
print("=" * 60)
print("EXTRACTION COMPLETE")
print("=" * 60)

print(f"PDFs found:          {len(pdf_files)}")
print(f"PDFs processed:      {processed}")
print(f"PDFs successful:     {successful}")
print(f"PDFs failed:         {failed}")
print(f"Total pages:         {pages_total}")
print(f"Pages needing OCR:   {pages_needing_ocr}")

print()
print(f"Output:              {OUTPUT_FILE}")
print(f"Errors:              {ERROR_FILE}")