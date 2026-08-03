lines = open("generate_paper.py", encoding="utf-8").readlines()

insertions = []

# 1. Add a sentence to the crisis engine section about clinical relevance
for i, line in enumerate(lines):
    if 'The halting protocol, which models escalation from psychologist notification' in line:
        insertions.append((i, 'halting'))
        break

# 2. Add to the discussion about the threshold boundary issue  
for i, line in enumerate(lines):
    if 'boundary cases represent inherent ambiguity in any hard-threshold classification' in line:
        insertions.append((i, 'boundary'))
        break

# 3. Add to the conclusion about validation timeline
for i, line in enumerate(lines):
    if 'Fourth, development of a clinical data collection protocol for IRB-approved validation' in line:
        insertions.append((i, 'timeline'))
        break

# Process in reverse order
insertions.sort(key=lambda x: x[0], reverse=True)

for idx, label in insertions:
    if label == 'halting':
        lines.insert(idx+1, '    "The 101 ms overhead includes thread creation, state initialization, and the initial "\n')
        lines.insert(idx+2, '    "crisis assessment call. This benchmark confirms that the crisis engine is not a "\n')
        lines.insert(idx+3, '    "performance bottleneck even at 25 times the expected single-patient concurrency."\n')
        print(f"Added halting context at line {idx}")
        
    elif label == 'boundary':
        lines.insert(idx+1, '    "In clinical practice, such boundary cases would likely be reviewed by the clinician "\n')
        lines.insert(idx+2, '    "alongside the flagged profiles, and the false positive rate of 9 percent is acceptable "\n')
        lines.insert(idx+3, '    "for a triage system where the cost of a false negative (missed deterioration) far "\n')
        lines.insert(idx+4, '    "exceeds the cost of a false positive (unnecessary review)."\n')
        print(f"Added boundary context at line {idx}")

    elif label == 'timeline':
        lines.insert(idx+1, '    "The pilot is expected to run for six months with monthly reporting on discrepancy "\n')
        lines.insert(idx+2, '    "detection rates, clinician review burden, and user acceptance from both patients "\n')
        lines.insert(idx+3, '    "and clinicians."\n')
        print(f"Added timeline at line {idx}")

open("generate_paper.py", "w", encoding="utf-8").write("".join(lines))
print("Done")
