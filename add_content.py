with open("generate_paper.py", encoding="utf-8") as f:
    content = f.read()

# Find the wearable paragraph end
anchor1 = 'medical-grade wearables, which would add significant cost and logistical complexity.'
insert1 = 'medical-grade wearables, which would add significant cost and logistical complexity. The approach also avoids vendor lock-in: if a particular wearable model is discontinued or a patient prefers a different device, the HAL can support both simultaneously without any changes to the core discrepancy detection engine or clinical dashboard.'

if anchor1 in content:
    content = content.replace(anchor1, insert1, 1)
    print("1. Expanded Introduction - wearable paragraph")
else:
    print("1. FAILED")

# Find the open-source license line
anchor2 = 'The system is released under an'
# Check the exact text
idx = content.find(anchor2)
if idx != -1:
    end = content.find('\n', idx)
    print(f"Found: {repr(content[idx:end])}")

# Expand the last long-term paragraph in conclusion
anchor3 = 'The system is released under an "\n    "open-source license."'
insert3 = 'The system is released under an "\n    "open-source license. The open-source model was chosen deliberately to enable "\n    "independent security auditing, community-driven adapter development for new wearable "\n    "devices, and collaborative extension of the rule-based discrepancy engine to support "\n    "additional languages and cultural contexts of distress expression."'

# Try to find it as raw string
import re
pattern = r'The system is released under an "'
matches = list(re.finditer(pattern, content))
if matches:
    m = matches[0]
    print(f"Found at {m.start()}: {repr(content[m.start():m.start()+200])}")

with open("generate_paper.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Done")
