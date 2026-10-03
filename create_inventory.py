from pathlib import Path
import csv

COURSES_DIR = Path(r"C:\Users\ajay singh\Desktop\courses")

OUTPUT_FILE = Path("file_inventory.csv")

# Files that are potentially useful for our knowledge base
USEFUL_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".pptx",
    ".ppt",
    ".txt",
    ".md",
    ".markdown",
    ".ipynb",
    ".xlsx",
    ".xls",
    ".csv",
    ".jpg",
    ".jpeg",
    ".png",
}

# Obvious temporary/junk files
JUNK_PREFIXES = (
    "~$",
)

JUNK_EXTENSIONS = {
    ".tlog",
    ".obj",
    ".pdb",
    ".ilk",
    ".lastbuildstate",
    ".filters",
    ".vcxproj",
    ".vcproj",
    ".sln",
    ".suo",
    ".user",
    ".vsidx",
    ".bak",
    ".tmp",
    ".log",
    ".dll",
    ".exe",
}

rows = []

for file in COURSES_DIR.rglob("*"):

    if not file.is_file():
        continue

    relative_path = file.relative_to(COURSES_DIR)

    # Determine top-level folder
    if len(relative_path.parts) > 1:
        top_folder = relative_path.parts[0]
    else:
        top_folder = "[ROOT]"

    extension = file.suffix.lower()

    # Classify file
    if file.name.startswith(JUNK_PREFIXES):
        category = "temporary"

    elif extension in JUNK_EXTENSIONS:
        category = "likely_generated"

    elif extension in USEFUL_EXTENSIONS:
        category = "potential_knowledge"

    else:
        category = "unknown"

    rows.append({
        "top_folder": top_folder,
        "filename": file.name,
        "extension": extension,
        "size_kb": round(file.stat().st_size / 1024, 2),
        "category": category,
        "relative_path": str(relative_path),
    })


# Write CSV
with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "top_folder",
            "filename",
            "extension",
            "size_kb",
            "category",
            "relative_path",
        ],
    )

    writer.writeheader()
    writer.writerows(rows)


print("=" * 60)
print("INVENTORY CREATED")
print("=" * 60)

print(f"\nTotal files analyzed: {len(rows)}")

from collections import Counter

counts = Counter(row["category"] for row in rows)

print("\nCategories:")

for category, count in counts.most_common():
    print(f"  {category:20} {count}")

print(f"\nInventory saved to:")
print(OUTPUT_FILE.absolute())