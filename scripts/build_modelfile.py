"""Generate Modelfile from downloaded dataset examples for Sentinel custom model."""
import json, os, random

random.seed(42)

cache = os.path.join(os.path.dirname(__file__), "dataset_examples")

def load(name):
    with open(os.path.join(cache, f"{name}.json"), encoding="utf-8") as f:
        return json.load(f)

def esc(text):
    """Escape backslash and double-quote for Modelfile MESSAGE body."""
    return text.replace("\\", "\\\\").replace('"', '\\"')

print("Loading datasets...")
emotion = load("emotion")
mental_health = load("mental_health_chatbot_dataset")
counsel = load("counsel-chat")

# Map emotion labels
emotion_labels = {0: "sadness", 1: "joy", 2: "love", 3: "anger", 4: "fear", 5: "surprise"}

# Build few-shot examples — select diverse samples
few_shot = []

# 1. Emotion classification examples (5)
for item in random.sample(emotion, 8):
    label_name = emotion_labels.get(item["label"], f"label_{item['label']}")
    few_shot.append(("user", f"Classify the emotion in this text: \"{item['text']}\""))
    few_shot.append(("assistant", f"The emotion expressed is {label_name}."))

# 2. Mental health Q&A (6)
for item in random.sample(mental_health, min(8, len(mental_health))):
    txt = item["text"].replace("<HUMAN>:", "").replace("<ASSISTANT>:", "").strip()
    resp = item["response"].strip()
    if txt and resp and len(txt) < 300 and len(resp) < 400:
        few_shot.append(("user", txt[:300]))
        few_shot.append(("assistant", resp[:400]))

# 3. CounselChat therapy Q&A (6)
for item in random.sample(counsel, min(8, len(counsel))):
    q = item.get("questionText", item.get("questionTitle", ""))
    a = item.get("answerText", "")
    if q and a and len(q) < 300 and len(a) < 400:
        few_shot.append(("user", q[:300]))
        few_shot.append(("assistant", a[:400]))

# 4. Clinical note generation examples (synthetic but realistic)
clinical_examples = [
    (
        "Summarize this journal entry for a psychologist: \"Had a rough day. Couldn't stop thinking about the argument with my partner. Felt my heart racing all afternoon. Didn't eat much.\"",
        "Patient reports interpersonal conflict with partner, accompanied by somatic symptoms (tachycardia, reduced appetite) and rumination. Emotional state suggests moderate distress. No acute crisis indicators. Monitor for mood trends and consider follow-up discussion."
    ),
    (
        "Generate a clinical note from this session observation: \"Patient reported improved sleep this week, averaging 6-7 hours. Still feeling anxious about work deadlines but using breathing techniques with some success. Mood generally stable.\"",
        "Observations: Patient reports improved sleep hygiene (6-7 hrs/night) and partial success with anxiety management techniques. Work-related stress remains but coping strategies show initial effectiveness.\nAssessment: Mild anxiety symptoms with good insight and treatment adherence. No acute concerns.\nPlan: Continue current therapeutic approach. Introduce cognitive restructuring for work-related anxiety triggers. Follow-up in 2 weeks."
    ),
    (
        "Assess risk in this journal: \"I feel so alone. Nobody understands what I'm going through. Sometimes I wonder if anyone would notice if I just disappeared.\"",
        "risk_score: 7\nreasoning: Patient expresses social isolation and existential despair with passive suicidal ideation ('would anyone notice if I disappeared'). Requires immediate clinical attention and safety assessment. No active plan or means disclosed, but statements warrant urgent follow-up.\ntriggered: true"
    ),
    (
        "Classify the emotional tone: \"I'm so excited! I got the job I've been working toward for months!\"",
        "The emotional tone is joy/excitement. Positive achievement-oriented affect with high energy."
    ),
]

for q, a in clinical_examples:
    few_shot.append(("user", q))
    few_shot.append(("assistant", a))

print(f"Total few-shot examples: {len(few_shot) // 2}")

system_prompt = """You are Sentinel, a specialized clinical AI assistant for mental health professionals. Your expertise is analyzing patient journal entries, biometric data, and therapy session records.

CORE CAPABILITIES:
1. JOURNAL SUMMARIZATION — Convert raw patient journal entries into brief, emotionally neutral clinical summaries. Focus on emotional state, concerns, and wellbeing indicators.
2. CLINICAL NOTE GENERATION — Produce structured SOAP-format notes (Observations, Assessment, Plan) from session observations.
3. RISK ASSESSMENT — Identify crisis indicators: passive/active suicidal ideation, self-harm, severe distress. Flag immediately with risk_score (1-10).
4. EMOTION CLASSIFICATION — Identify emotional tone from text: sadness, joy, love, anger, fear, surprise, anxiety, hope, grief, etc.
5. BIOMETRIC ANALYSIS — Correlate biodata (heart rate, sleep, stress) with reported emotional state.

GUIDELINES:
- Maintain professional, clinical tone at all times
- Be specific and concise — avoid generic therapy suggestions
- Never diagnose specific conditions — describe symptoms and patterns
- Flag potential crisis indicators immediately with clear language
- Reference specific details from the input rather than generalities
- When suggesting therapeutic approaches, ground them in the patient's specific presentation"""

# Build Modelfile
modelfile_lines = [
    f"FROM mistral:latest",
    f"",
    f'SYSTEM """{system_prompt}"""',
    f"",
    f"PARAMETER temperature 0.3",
    f"PARAMETER top_p 0.9",
    f"PARAMETER num_ctx 4096",
    f"",
    "# Few-shot training examples from curated datasets",
    f"",
]

for role, content in few_shot:
    modelfile_lines.append(f'MESSAGE {role} "{esc(content)}"')

modelfile_path = os.path.join(os.path.dirname(__file__), "Modelfile")
with open(modelfile_path, "w", encoding="utf-8") as f:
    f.write("\n".join(modelfile_lines))

print(f"Modelfile written to {modelfile_path}")
print(f"Size: {os.path.getsize(modelfile_path)} bytes")
