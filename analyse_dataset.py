from pathlib import Path
from collections import Counter, defaultdict

COURSES_DIR = Path(r"C:\Users\ajay singh\Desktop\courses")

# File types that are potentially useful for our knowledge base
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

files = [f for f in COURSES_DIR.rglob("*") if f.is_file()]

# Group files by their top-level folder
folder_files = defaultdict(list)

for file in files:
    relative = file.relative_to(COURSES_DIR)

    if len(relative.parts) > 1:
        top_folder = relative.parts[0]
    else:
        top_folder = "[ROOT]"

    folder_files[top_folder].append(file)


print("=" * 70)
print("B.TECH BRAIN - DATASET ANALYSIS")
print("=" * 70)

print(f"\nTotal files: {len(files)}")

# --------------------------------------------------
# Useful vs potentially irrelevant
# --------------------------------------------------

useful_files = [
    f for f in files
    if f.suffix.lower() in USEFUL_EXTENSIONS
]

other_files = [
    f for f in files
    if f.suffix.lower() not in USEFUL_EXTENSIONS
]

print(f"\nPotentially useful files: {len(useful_files)}")
print(f"Other files: {len(other_files)}")

# --------------------------------------------------
# Useful file types
# --------------------------------------------------

extensions = Counter(
    f.suffix.lower() if f.suffix else "[no extension]"
    for f in useful_files
)

print("\nPotentially useful file types:")

for ext, count in extensions.most_common():
    print(f"  {ext:10} {count}")

# --------------------------------------------------
# Files by folder
# --------------------------------------------------

print("\n" + "=" * 70)
print("FILES BY TOP-LEVEL FOLDER")
print("=" * 70)

for folder, folder_list in sorted(
    folder_files.items(),
    key=lambda x: len(x[1]),
    reverse=True
):
    useful_count = sum(
        f.suffix.lower() in USEFUL_EXTENSIONS
        for f in folder_list
    )

    print(
        f"{folder:30} "
        f"Total: {len(folder_list):5}   "
        f"Useful candidates: {useful_count:5}"
    )

# --------------------------------------------------
# Sample useful files
# --------------------------------------------------

print("\n" + "=" * 70)
print("SAMPLE USEFUL FILES")
print("=" * 70)

for file in useful_files[:100]:
    print(file.relative_to(COURSES_DIR))

print("\n" + "=" * 70)