from pathlib import Path
from collections import Counter

COURSES_DIR = Path(r"C:\Users\ajay singh\Desktop\courses")

extensions = Counter()

for file in COURSES_DIR.rglob("*"):
    if file.is_file():
        ext = file.suffix.lower()

        if not ext:
            ext = "[NO EXTENSION]"

        extensions[ext] += 1

print("=" * 60)
print("ALL FILE EXTENSIONS")
print("=" * 60)

print(f"\nUnique extensions: {len(extensions)}\n")

for ext, count in extensions.most_common():
    print(f"{ext:20} {count:6}")