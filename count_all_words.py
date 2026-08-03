import re

with open("generate_paper.py", encoding="utf-8") as f:
    content = f.read()

# Get content from Introduction to References
ref_idx = content.find('p.section("", "References")')
intro_idx = content.find('p.section("1", "Introduction")')
body = content[intro_idx:ref_idx]

# Count ALL text in body(), multi_cell(), cell(), section(), subsection(), make_table()
all_strings = re.findall(r'"([^"]*)"', body)

total_words = 0
for s in all_strings:
    s = s.strip()
    if not s:
        continue
    # Skip config strings
    if s in ("AR", "P", "mm", "A4", "B", "I", "BI", "C", "L", "1", "2", "3", "4", "5", "6"):
        continue
    if s.startswith("C:\\"):
        continue
    if re.match(r"^\\u[\da-f]{4}$", s):
        continue
    total_words += len(s.split())

print(f"Total rendered words (all sources): {total_words}")
