from pathlib import Path
import csv
import json
import hashlib

import pymupdf
import pytesseract
from PIL import Image


# =========================================================
# CONFIG
# =========================================================

DATASET_ROOT = Path(
    r"C:\Users\ajay singh\Desktop\courses"
)

PROFILE_FILE = Path(
    "document_profile.csv"
)

INPUT_PAGES_FILE = Path(
    "processed/pdf_pages.jsonl"
)

OUTPUT_DIR = Path(
    "processed/ocr"
)

OUTPUT_FILE = OUTPUT_DIR / "pdf_pages_ocr.jsonl"
ERROR_FILE = OUTPUT_DIR / "ocr_errors.jsonl"

TESSERACT_PATH = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

DPI = 300


# =========================================================
# OCR CONFIGURATION
# =========================================================

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


# =========================================================
# HELPERS
# =========================================================

def normalize_text(text):
    """
    Conservative text normalization.

    We do NOT try to correct spelling, equations,
    terminology, or academic content.
    """

    if not text:
        return ""

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    return text.strip()


def calculate_sha256(path):
    """
    Calculate file hash without loading the whole file.
    """

    sha = hashlib.sha256()

    with path.open("rb") as f:

        while True:

            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            sha.update(chunk)

    return sha.hexdigest()


# =========================================================
# LOAD DOCUMENT PROFILE
# =========================================================

if not PROFILE_FILE.exists():

    raise FileNotFoundError(
        f"Missing {PROFILE_FILE}. "
        "Run document_profiler.py first."
    )


profiles = {}

with PROFILE_FILE.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:

    reader = csv.DictReader(f)

    for row in reader:

        path_value = row.get(
            "path",
            ""
        ).strip()

        if path_value:

            profiles[path_value] = row


print(
    f"Loaded profile for {len(profiles)} PDFs."
)


# =========================================================
# LOAD EXISTING EXTRACTION DATA
# =========================================================

if not INPUT_PAGES_FILE.exists():

    raise FileNotFoundError(
        f"Missing {INPUT_PAGES_FILE}. "
        "Run extract_pdfs.py first."
    )


# =========================================================
# PREPARE OUTPUT
# =========================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# Start fresh
OUTPUT_FILE.write_text(
    "",
    encoding="utf-8"
)

ERROR_FILE.write_text(
    "",
    encoding="utf-8"
)


# =========================================================
# PROCESS
# =========================================================

processed_pages = 0
ocr_pages = 0
native_pages = 0
empty_ocr_pages = 0
ocr_errors = 0


current_pdf = None
current_doc = None


def close_current_pdf():

    global current_doc

    if current_doc is not None:

        try:
            current_doc.close()
        except Exception:
            pass

        current_doc = None


with INPUT_PAGES_FILE.open(
    "r",
    encoding="utf-8"
) as input_f, OUTPUT_FILE.open(
    "a",
    encoding="utf-8"
) as output_f, ERROR_FILE.open(
    "a",
    encoding="utf-8"
) as error_f:

    for line in input_f:

        record = json.loads(line)

        source_path = record["source_path"]

        # -------------------------------------------------
        # Open PDF only when we encounter a new document
        # -------------------------------------------------

        if source_path != current_pdf:

            close_current_pdf()

            current_pdf = source_path

            pdf_path = (
                DATASET_ROOT / source_path
            )

            try:

                current_doc = pymupdf.open(
                    pdf_path
                )

            except Exception as error:

                error_record = {
                    "source_path": source_path,
                    "error": str(error),
                    "stage": "open_pdf"
                }

                error_f.write(
                    json.dumps(
                        error_record,
                        ensure_ascii=False
                    ) + "\n"
                )

                ocr_errors += 1

                current_doc = None

        # -------------------------------------------------
        # Base record
        # -------------------------------------------------

        native_text = normalize_text(
            record.get("text", "")
        )

        page_number = record["page"]

        # -------------------------------------------------
        # Default: preserve existing native text
        # -------------------------------------------------

        ocr_used = False
        ocr_text = ""
        ocr_error = None

        # -------------------------------------------------
        # OCR ONLY WHEN NATIVE TEXT IS EMPTY
        # -------------------------------------------------

        if not native_text:

            if current_doc is None:

                ocr_error = (
                    "PDF could not be opened"
                )

                ocr_errors += 1

            else:

                ocr_used = True
                ocr_pages += 1

                try:

                    page = current_doc[
                        page_number - 1
                    ]

                    zoom = DPI / 72

                    matrix = pymupdf.Matrix(
                        zoom,
                        zoom
                    )

                    pix = page.get_pixmap(
                        matrix=matrix,
                        alpha=False
                    )

                    image = Image.frombytes(
                        "RGB",
                        [
                            pix.width,
                            pix.height
                        ],
                        pix.samples
                    )

                    ocr_text = pytesseract.image_to_string(
                        image,
                        lang="eng"
                    )

                    ocr_text = normalize_text(
                        ocr_text
                    )

                    if not ocr_text:

                        empty_ocr_pages += 1

                except Exception as error:

                    ocr_errors += 1

                    ocr_error = str(error)

                    error_record = {
                        "source_path": source_path,
                        "page": page_number,
                        "error": str(error),
                        "stage": "ocr"
                    }

                    error_f.write(
                        json.dumps(
                            error_record,
                            ensure_ascii=False
                        ) + "\n"
                    )

        else:

            native_pages += 1

        # -------------------------------------------------
        # Build final record
        # -------------------------------------------------

        profile = profiles.get(
            source_path,
            {}
        )

        output_record = {
            "source_path": source_path,

            "file_name": record.get(
                "file_name"
            ),

            "source_folder": record.get(
                "source_folder"
            ),

            "page": page_number,

            "page_count": record.get(
                "page_count"
            ),

            "sha256": record.get(
                "sha256"
            ),

            "duplicate_count": record.get(
                "duplicate_count",
                1
            ),

            "document_classification": record.get(
                "document_classification"
            ),

            # Original native PDF extraction
            "native_text": native_text,

            "native_char_count": len(
                native_text
            ),

            # OCR result kept separately
            "ocr_used": ocr_used,

            "ocr_text": ocr_text,

            "ocr_char_count": len(
                ocr_text
            ),

            "ocr_dpi": DPI if ocr_used else None,

            "ocr_error": ocr_error,

            # Useful downstream signal
            "text_source": (
                "native"
                if native_text
                else (
                    "ocr"
                    if ocr_text
                    else "none"
                )
            )
        }

        output_f.write(
            json.dumps(
                output_record,
                ensure_ascii=False
            ) + "\n"
        )

        processed_pages += 1

        # -------------------------------------------------
        # Progress
        # -------------------------------------------------

        if processed_pages % 500 == 0:

            print(
                f"[{processed_pages}] pages processed | "
                f"OCR: {ocr_pages} | "
                f"native: {native_pages} | "
                f"empty OCR: {empty_ocr_pages} | "
                f"errors: {ocr_errors}"
            )


# =========================================================
# CLEANUP
# =========================================================

close_current_pdf()


# =========================================================
# FINAL REPORT
# =========================================================

print()
print("=" * 70)
print("FULL OCR PIPELINE COMPLETE")
print("=" * 70)

print(
    f"Pages processed:       {processed_pages}"
)

print(
    f"Native-text pages:     {native_pages}"
)

print(
    f"OCR pages:             {ocr_pages}"
)

print(
    f"OCR pages with no text:{empty_ocr_pages}"
)

print(
    f"Errors:                {ocr_errors}"
)

print()
print(
    f"Output: {OUTPUT_FILE}"
)

print(
    f"Errors: {ERROR_FILE}"
)

print("=" * 70)