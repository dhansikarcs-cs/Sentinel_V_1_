lines = open("generate_paper.py", encoding="utf-8").readlines()
changes = []

# 1. Add to Discussion - implications after the acceptable trade-offs paragraph
for i, line in enumerate(lines):
    if 'acceptable. Table 5 summarizes the comparison across key architectural dimensions.' in line:
        changes.append(('discussion_implications', i))
        break

# 2. Add to Conclusion - impact metrics  
for i, line in enumerate(lines):
    if 'The key contributions are:' in line:
        changes.append(('conclusion_contributions', i))
        break

# 3. Add to Introduction - digital divide context
for i, line in enumerate(lines):
    if 'Technology-assisted monitoring offers a scalable alternative that extends the reach' in line:
        changes.append(('intro_digital', i))
        break

# 4. Add future work item - mobile app
for i, line in enumerate(lines):
    if 'Fourth, development of a clinical data collection protocol for IRB-approved validation' in line:
        changes.append(('future_app', i))
        break

print(f"Found {len(changes)} insertion points")

# Sort in reverse order to not mess up line numbers
changes.sort(key=lambda x: x[1], reverse=True)

for label, idx in changes:
    if label == 'discussion_implications':
        lines.insert(idx+1, 'p.body(\n')
        lines.insert(idx+2, '    "The clinical implication is that Sentinel can extend the monitoring coverage of "\n')
        lines.insert(idx+3, '    "a single clinician from one hour per week per patient to around-the-clock passive "\n')
        lines.insert(idx+4, '    "surveillance, at a hardware cost of approximately 200 USD for a 30-patient caseload. "\n')
        lines.insert(idx+5, '    "While the system cannot replace clinical judgment, it can prioritize clinician attention "\n')
        lines.insert(idx+6, '    "toward patients whose subjective and objective channels are incongruent, potentially "\n')
        lines.insert(idx+7, '    "identifying deteriorating patients earlier than scheduled appointments would allow."\n')
        lines.insert(idx+8, ')\n')
        print(f"Added discussion implications at line {idx}")
        
    elif label == 'conclusion_contributions':
        lines.insert(idx+1, '    "Sentinel demonstrates that an on-premises psychophysiological monitoring platform can be "\n')
        lines.insert(idx+2, '    "engineered at low cost while incorporating security measures appropriate for protected "\n')
        lines.insert(idx+3, '    "health information. The system addresses a specific gap in the current digital mental health "\n')
        lines.insert(idx+4, '    "landscape: the absence of a low-cost, offline-capable, discrepancy-based triage platform "\n')
        lines.insert(idx+5, '    "that fuses wearable biometrics with patient-reported mental state. "\n')
        print(f"Added conclusion lead-in at line {idx}")

    elif label == 'intro_digital':
        lines.insert(idx+1, '    "However, technology-assisted monitoring must account for the digital divide: patients in "\n')
        lines.insert(idx+2, '    "low-resource settings may have limited access to smartphones, reliable internet, or the "\n')
        lines.insert(idx+3, '    "latest wearable devices. Sentinel addresses this constraint by operating on-premises with "\n')
        lines.insert(idx+4, '    "no internet requirement for core functionality and by supporting a range of wearable devices "\n')
        lines.insert(idx+5, '    "at different price points, from basic fitness bands to advanced smart rings. "\n')
        print(f"Added intro digital divide at line {idx}")

    elif label == 'future_app':
        lines.insert(idx+1, '    "Fifth, development of a companion mobile application for patient journal entry and "\n')
        lines.insert(idx+2, '    "wearable data synchronization, reducing reliance on desktop browser access and "\n')
        lines.insert(idx+3, '    "improving the patient experience for daily journal submissions. "\n')
        print(f"Added future work item at line {idx}")

open("generate_paper.py", "w", encoding="utf-8").write("".join(lines))
print("Done")
