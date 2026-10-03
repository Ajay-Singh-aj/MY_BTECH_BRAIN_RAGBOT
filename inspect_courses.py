from pathlib import Path
from collections import Counter

COURSES_DIR = Path(r"C:\Users\ajay singh\Desktop\courses")

if not COURSES_DIR.exists():
    print("ERROR: courses folder was not found.")
    print(f"Checked: {COURSES_DIR}")
    raise SystemExit

files = [f for f in COURSES_DIR.rglob("*") if f.is_file()]

print("=" * 60)
print("MY B.TECH BRAIN - DATASET INSPECTION")
print("=" * 60)

print(f"\nTotal files: {len(files)}")

extensions = Counter(
    f.suffix.lower() if f.suffix else "[no extension]"
    for f in files
)

print("\nFile types:")
for extension, count in extensions.most_common():
    print(f"  {extension:15} {count}")

folders = [f for f in COURSES_DIR.iterdir() if f.is_dir()]

print(f"\nTop-level folders: {len(folders)}")

print("\nFolder names:")
for folder in folders:
    print(f"  - {folder.name}")

print("\n" + "=" * 60)