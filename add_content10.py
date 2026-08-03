lines = open("generate_paper.py", encoding="utf-8").readlines()

insertions = []

# Add a paragraph about the frontend performance 
for i, line in enumerate(lines):
    if 'State management is handled through React Context with separate typed contexts for' in line:
        insertions.append((i, 'frontend'))
        break

# Add a paragraph about NLP limitations nuance
for i, line in enumerate(lines):
    if '# 5. DISCUSSION AND LIMITATIONS' in line:
        insertions.append((i, 'nlp'))
        break

insertions.sort(key=lambda x: x[0], reverse=True)

for idx, label in insertions:
    if label == 'frontend':
        lines.insert(idx-2, '    "The frontend communicates with the backend exclusively through the REST API, with "\n')
        lines.insert(idx-1, '    "no direct database access from the browser. All data fetching, form submission, and "\n')
        lines.insert(idx, '    "state updates pass through authenticated API calls logged in the audit trail."\n')
        # Fix the inserted line - remove from original location
        print(f"Added frontend at {idx}")
    elif label == 'nlp':
        # Add before the discussion section
        pass

open("generate_paper.py", "w", encoding="utf-8").write("".join(lines))
print("Done")
