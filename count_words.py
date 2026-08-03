# This script counts words from the Introduction through Conclusion (excludes title, refs, AI disclosure)

import re

with open("generate_paper.py", "r", encoding="utf-8") as f:
    content = f.read()

ref_idx = content.find('p.section("", "References")')
intro_idx = content.find('p.section("1", "Introduction")')
body = content[intro_idx:ref_idx]

# Prose
matches = re.findall(r"p\.(?:body|multi_cell)\([^)]*\)", body)
text_parts = []
for m in matches:
    parts = re.findall(r'"([^"]*)"', m)
    text_parts.extend(parts)
body_words = len(" ".join(text_parts).split())

# Section/subsection titles
title_matches = re.findall(r"p\.(?:section|subsection)\([^)]*\)", body)
title_text = []
for m in title_matches:
    parts = re.findall(r'"([^"]*)"', m)
    for p in parts:
        if p.isdigit() or p == "":
            continue
        title_text.append(p)
title_words = len(" ".join(title_text).split())

# Table data
table_matches = re.findall(r"p\.make_table\([^)]*\)", body)
table_words = 0
for m in table_matches:
    parts = re.findall(r'"([^"]*)"', m)
    for p in parts:
        if re.match(r"^[\d,.%\s]+$", p):
            continue
        table_words += len(p.split())

total = body_words + title_words + table_words
print(f"Body (prose): {body_words}")
print(f"Sections:     {title_words}")
print(f"Tables:       {table_words}")
print(f"Total:        {total}")
