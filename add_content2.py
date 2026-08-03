content = open("generate_paper.py", encoding="utf-8").read()

old = 'The system is released under an "\n    "open-source license."'
new = 'The system is released under an "\n    "open-source license. The open-source model was deliberately chosen to enable "\n    "independent security auditing by third-party researchers, community-driven adapter "\n    "development for new wearable devices, and collaborative extension of the discrepancy "\n    "engine to support additional languages and cultural contexts of distress expression."'

if old in content:
    content = content.replace(old, new, 1)
    open("generate_paper.py", "w", encoding="utf-8").write(content)
    print("Done - expanded open-source license sentence")
else:
    print("Not found - trying exact match")
    # Debug
    idx = content.find('open-source license')
    if idx != -1:
        print(repr(content[idx-10:idx+80]))
