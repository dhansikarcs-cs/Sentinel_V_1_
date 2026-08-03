content = open("generate_paper.py", encoding="utf-8").read()

old = 'available. This also means that during normal operation with Tier 1 or Tier 2 active, '
new = 'available. This also means that during normal operation with Tier 1 or Tier 2 active, '
old2 = 'the total latency for journal processing is dominated by the AI inference time rather '
new2 = 'the total latency for journal processing is dominated by the AI inference time rather '

# Check what's there after 'AI services are'
idx = content.find('rule-based fallback in the production system')
if idx != -1:
    # Find the sentence end
    snippet = content[idx:idx+400]
    print(repr(snippet[:300]))

# Insert before 'This also means'  
old_text = 'available. This also means that during normal operation with Tier 1 or Tier 2 active,'
new_text = 'available. The design also enables a useful developer workflow: engineers can disable Tier 1 and Tier 2 during development and testing to force deterministic behavior and obtain reproducible test results without AI nondeterminism, then re-enable both tiers for production deployment to gain the benefit of contextual language understanding. This also means that during normal operation with Tier 1 or Tier 2 active,'

if old_text in content:
    content = content.replace(old_text, new_text, 1)
    open("generate_paper.py", "w", encoding="utf-8").write(content)
    print("Expanded AI section")
else:
    print("Not found")
    print(repr(content[idx:idx+200]))
