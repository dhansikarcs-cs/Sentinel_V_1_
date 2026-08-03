content = open("generate_paper.py", encoding="utf-8").read()

# ==========================================
# 1. Expand Introduction - add cost burden
# ==========================================
old1 = 'closing this gap through in-person services alone would require a five-fold increase in the mental health workforce, an investment that is unlikely to materialize in the near term.'
insert1 = 'closing this gap through in-person services alone would require a five-fold increase in the mental health workforce, an investment that is unlikely to materialize in the near term. The economic burden is equally severe: mental health conditions cost the global economy an estimated 1 trillion USD annually in lost productivity, and this figure is projected to double by 2030 without effective scalable interventions.'

if old1 in content:
    content = content.replace(old1, insert1, 1)
    print("1. Expanded Introduction cost burden")
else:
    print("1. FAILED")

# ==========================================
# 2. Expand System Architecture section
# ==========================================
old2 = 'and a defense-in-depth security model incorporating encryption, network isolation, and tamper-evident audit logging.'
insert2 = 'and a defense-in-depth security model incorporating encryption, network isolation, and tamper-evident audit logging. The following subsections describe each component in detail, with the empirical validation of the complete system presented in Section 4.'

if old2 in content:
    content = content.replace(old2, insert2, 1)
    print("2. Expanded Architecture overview")
else:
    print("2. FAILED")

# ==========================================
# 3. Expand Conclusion - add timeline and impact
# ==========================================
old3 = 'for 5 to 10 years of continuous operation.'
# Check if this exists
if old3 in content:
    print("3. Storage sentence exists at:", content.find(old3))

# More reliable: add to the conclusion long-term paragraph  
old4 = 'The open-source model was deliberately chosen to enable '
insert4 = 'The open-source model was deliberately chosen, following the principles of reproducible research in computational biomedicine, to enable '

if old4 in content:
    content = content.replace(old4, insert4, 1)
    print("4. Expanded open-source rationale")
else:
    print("4. FAILED")

open("generate_paper.py", "w", encoding="utf-8").write(content)
print("Done")
