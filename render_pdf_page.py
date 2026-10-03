from pathlib import Path
import sys

from pypdf import PdfReader


if len(sys.argv) < 3:
    print("Usage:")
    print(
        'python render_pdf_page.py '
        '"3rd SEm\\ARTS201\\module 1 c.pdf" 4'
    )
    sys.exit(1)


pdf_path = Path(sys.argv[1])
page_number = int(sys.argv[2])

if not pdf_path.exists():
    print(f"PDF not found: {pdf_path}")
    sys.exit(1)


reader = PdfReader(str(pdf_path))

if page_number < 1 or page_number > len(reader.pages):
    print(
        f"Invalid page number. "
        f"Document has {len(reader.pages)} pages."
    )
    sys.exit(1)


page = reader.pages[page_number - 1]

images = list(page.images)

print("=" * 70)
print(f"PDF: {pdf_path}")
print(f"Page: {page_number}")
print(f"Embedded images found: {len(images)}")
print("=" * 70)

for i, image in enumerate(images, start=1):

    output_dir = Path("processed") / "page_images"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = (
        output_dir /
        f"{pdf_path.stem}_page_{page_number}_image_{i}"
        f"{Path(image.name).suffix}"
    )

    with output_file.open("wb") as f:
        f.write(image.data)

    print(f"Saved: {output_file}")
    