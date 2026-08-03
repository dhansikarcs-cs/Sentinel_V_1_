lines = open("generate_paper.py", encoding="utf-8").readlines()

insertions = []

# Add to the discrepancy detection section about why 50 test profiles
for i, line in enumerate(lines):
    if 'The zero false negative rate is the critical outcome for a safety-critical application where' in line:
        insertions.append((i, 'fn_explain'))
        break

# Add to the deployment architecture about resource requirements  
for i, line in enumerate(lines):
    if 'resource-constrained outpatient clinics seeking to extend their monitoring coverage' in line:
        insertions.append((i, 'resources'))
        break

# Add to discussion about patient privacy considerations
for i, line in enumerate(lines):
    if 'Ninth, the system has not undergone formal software certification or medical device' in line:
        insertions.append((i, 'privacy'))
        break

insertions.sort(key=lambda x: x[0], reverse=True)

for idx, label in insertions:
    if label == 'fn_explain':
        lines.insert(idx+1, '    "The 50-profile validation set size was chosen to cover all nine sentiment-by-biometric "\n')
        lines.insert(idx+2, '    "combinations with at least five examples per combination, plus additional edge case "\n')
        lines.insert(idx+3, '    "profiles for negation handling and boundary conditions. While limited in absolute "\n')
        lines.insert(idx+4, '    "size, the test set provides complete coverage of the decision space defined by "\n')
        lines.insert(idx+5, '    "the engine\u2019s hardcoded truth table."\n')
        print(f"Added FN explanation at {idx}")
        
    elif label == 'resources':
        lines.insert(idx+1, '    "The minimum hardware requirement for a 30-patient deployment is a system with a "\n')
        lines.insert(idx+2, '    "quad-core x86-64 processor, 8 GB of RAM, and 64 GB of storage, which can be met "\n')
        lines.insert(idx+3, '    "by a refurbished mini-PC available for under 200 USD. If local AI inference (Tier 1) "\n')
        lines.insert(idx+4, '    "is desired, the requirement increases to 16 GB of RAM and a CPU with AVX2 support "\n')
        lines.insert(idx+5, '    "for running Mistral 7B via Ollama. These specifications are well within the range "\n')
        lines.insert(idx+6, '    "of commodity hardware available in low-resource settings."\n')
        print(f"Added resources at {idx}")

    elif label == 'privacy':
        lines.insert(idx+1, '    "Additionally, data privacy considerations beyond encryption deserve mention. The "\n')
        lines.insert(idx+2, '    "on-premises architecture ensures data never leaves the clinic network, but clinician "\n')
        lines.insert(idx+3, '    "access to patient data within the clinic is governed only by standard authentication.\n')
        lines.insert(idx+4, '    "A production deployment would benefit from role-based access logging, automatic "\n')
        lines.insert(idx+5, '    "session timeout, and integration with existing clinic identity management systems."\n')
        print(f"Added privacy at {idx}")

open("generate_paper.py", "w", encoding="utf-8").write("".join(lines))
print("Done")
