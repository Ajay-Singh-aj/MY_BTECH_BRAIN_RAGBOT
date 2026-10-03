from pathlib import Path
from pypdf import PdfReader
import hashlib
import csv
import re
from collections import defaultdict, Counter

COURSES_DIR = Path(r"C:\Users\ajay singh\Desktop\courses")
OUTPUT_FILE = Path("document_profile.csv")


def get_file_hash(path):
    """Create a hash of the actual PDF file."""
    sha256 = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            data = f.read(1024 * 1024)

            if not data:
                break

            sha256.update(data)

    return sha256.hexdigest()


def analyze_text(text):
    """Calculate simple text statistics."""

    text = text.strip()

    if not text:
        return {
            "characters": 0,
            "words": 0,
            "alphabetic_ratio": 0,
            "quality": "empty",
        }

    words = re.findall(r"\S+", text)

    alphabetic = sum(c.isalpha() for c in text)

    alphabetic_ratio = alphabetic / len(text)

    # We deliberately use a relaxed rule here.
    # Technical documents contain equations and symbols.
    if len(text) < 100:
        quality = "very_short"

    elif len(text) < 500:
        quality = "short"

    elif alphabetic_ratio < 0.15:
        quality = "suspicious"

    else:
        quality = "readable"

    return {
        "characters": len(text),
        "words": len(words),
        "alphabetic_ratio": round(alphabetic_ratio, 3),
        "quality": quality,
    }


def analyze_pdf(path):

    try:

        reader = PdfReader(str(path))

        pages = len(reader.pages)

        all_text = []

        pages_with_text = 0

        for page in reader.pages:

            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""

            text = text.strip()

            if len(text) > 50:
                pages_with_text += 1

            all_text.append(text)

        full_text = "\n".join(all_text)

        text_stats = analyze_text(full_text)

        if pages == 0:
            classification = "empty_pdf"

        else:

            text_ratio = pages_with_text / pages

            if text_ratio == 0:
                classification = "needs_ocr"

            elif text_ratio < 0.4:
                classification = "mostly_scanned"

            elif text_ratio < 0.9:
                classification = "mixed"

            else:

                if text_stats["quality"] == "readable":
                    classification = "readable"

                elif text_stats["quality"] == "short":
                    classification = "short_but_readable"

                elif text_stats["quality"] == "very_short":
                    classification = "very_short"

                else:
                    classification = "suspicious"

        return {
            "status": "success",
            "pages": pages,
            "pages_with_text": pages_with_text,
            "characters": text_stats["characters"],
            "words": text_stats["words"],
            "alphabetic_ratio": text_stats["alphabetic_ratio"],
            "classification": classification,
        }

    except Exception as e:

        return {
            "status": "error",
            "pages": 0,
            "pages_with_text": 0,
            "characters": 0,
            "words": 0,
            "alphabetic_ratio": 0,
            "classification": "error",
            "error": str(e),
        }


# --------------------------------------------------
# Find PDFs
# --------------------------------------------------

pdf_files = list(COURSES_DIR.rglob("*.pdf"))

print("=" * 70)
print("B.TECH BRAIN - DOCUMENT PROFILER")
print("=" * 70)

print(f"\nPDF files found: {len(pdf_files)}")
print("\nProfiling PDFs...")
print("This may take a few minutes.\n")


results = []

hash_groups = defaultdict(list)


# --------------------------------------------------
# Process PDFs
# --------------------------------------------------

for index, pdf_path in enumerate(pdf_files, start=1):

    relative_path = pdf_path.relative_to(COURSES_DIR)

    result = analyze_pdf(pdf_path)

    # Calculate exact file hash
    try:
        file_hash = get_file_hash(pdf_path)
        hash_groups[file_hash].append(str(relative_path))
    except Exception:
        file_hash = ""

    result["file"] = pdf_path.name
    result["path"] = str(relative_path)
    result["size_mb"] = round(
        pdf_path.stat().st_size / (1024 * 1024),
        2
    )
    result["sha256"] = file_hash

    results.append(result)

    print(
        f"[{index}/{len(pdf_files)}] "
        f"{result['classification']:20} "
        f"{relative_path}"
    )


# --------------------------------------------------
# Mark exact duplicates
# --------------------------------------------------

for result in results:

    duplicate_paths = hash_groups[result["sha256"]]

    if len(duplicate_paths) > 1:
        result["duplicate"] = "yes"
        result["duplicate_count"] = len(duplicate_paths)
    else:
        result["duplicate"] = "no"
        result["duplicate_count"] = 1


# --------------------------------------------------
# Save CSV
# --------------------------------------------------

fieldnames = [
    "file",
    "path",
    "size_mb",
    "status",
    "pages",
    "pages_with_text",
    "characters",
    "words",
    "alphabetic_ratio",
    "classification",
    "duplicate",
    "duplicate_count",
    "sha256",
    "error",
]


with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames,
        extrasaction="ignore"
    )

    writer.writeheader()
    writer.writerows(results)


# --------------------------------------------------
# Summary
# --------------------------------------------------

classification_counts = Counter(
    result["classification"]
    for result in results
)

duplicate_files = sum(
    1
    for result in results
    if result["duplicate"] == "yes"
)


print("\n")
print("=" * 70)
print("DOCUMENT PROFILE SUMMARY")
print("=" * 70)

for classification, count in classification_counts.most_common():

    print(
        f"{classification:25} {count}"
    )

print("\nExact duplicate files:", duplicate_files)

print("\nReport saved to:")
print(OUTPUT_FILE.absolute())

print("\nDone.")