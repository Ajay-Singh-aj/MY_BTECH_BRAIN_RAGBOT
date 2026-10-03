from pathlib import Path
import fitz  # PyMuPDF


PDF_FILE = Path(
    r"C:\Users\ajay singh\Desktop\courses\3rd SEm\ARTS201\module 1 c.pdf"
)

PAGE_NUMBER = 5

OUTPUT_DIR = Path("processed/highres_pages")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "module_1_c_page_5_300dpi.png"


if not PDF_FILE.exists():
    raise FileNotFoundError(PDF_FILE)


doc = fitz.open(PDF_FILE)

page = doc[PAGE_NUMBER - 1]

# 300 DPI rendering
zoom = 300 / 72

matrix = fitz.Matrix(zoom, zoom)

pix = page.get_pixmap(
    matrix=matrix,
    alpha=False
)

pix.save(OUTPUT_FILE)

print("=" * 70)
print("HIGH-RES PDF PAGE")
print("=" * 70)
print(f"PDF:       {PDF_FILE}")
print(f"Page:      {PAGE_NUMBER}")
print(f"Output:    {OUTPUT_FILE}")
print(f"Size:      {pix.width} x {pix.height}")
print("=" * 70)