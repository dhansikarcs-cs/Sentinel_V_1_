import json
import random
from pathlib import Path
from datetime import datetime, timedelta

random.seed(42)

OUT = Path(__file__).parent / "journal_synthetic_500.jsonl"

SCENARIOS = {
    "work": {
        "triggers": [
            "manager criticized", "deadline pressure", "meeting went badly",
            "got praised by boss", "finished a big project", "promoted",
            "colleague was rude", "layoffs announced", "new responsibility",
            "work from home again", "team lunch was nice", "boring meetings all day",
        ],
        "templates": [
            "Work was {trigger}. {feeling}.",
            "At work today, {trigger}. {reaction}",
            "Office was {trigger} today. {emotion}",
            "{trigger} at work. {aftermath}",
        ],
    },
    "relationships": {
        "triggers": [
            "fought with partner", "had a lovely date", "mom called",
            "friends ignored me", "made a new friend", "someone said they love me",
            "betrayed by someone I trusted", "apologized to my sibling",
            "helped a stranger today", "lonely all weekend",
            "partner was supportive", "argued with my parents",
        ],
        "templates": [
            "{trigger}. {feeling}.",
            "After {trigger}, I feel {emotion_word}.",
            "{trigger}. {reaction}",
            "Still thinking about how {trigger}. {aftermath}",
        ],
    },
    "health": {
        "triggers": [
            "woke up with a headache", "therapy session helped",
            "couldn't sleep again", "had a panic attack",
            "went for a run", "meditated for 10 minutes",
            "doctor gave good news", "felt dizzy at the store",
            "ate healthy all day", "slept 8 hours for once",
            "skipped medication", "therapy was tough today",
        ],
        "templates": [
            "{trigger}. {feeling}.",
            "Health-wise: {trigger}. {emotion}",
            "{trigger}. {aftermath}",
            "My body feels {trigger}. {reaction}",
        ],
    },
    "daily_life": {
        "triggers": [
            "cleaned the whole house", "lost my wallet",
            "cooked a nice meal", "car broke down",
            "found money in old jacket", "rained all day",
            "had a great coffee", "missed the bus",
            "read a good book", "spent hours on social media",
            "finally fixed the shelf", "internet was down",
        ],
        "templates": [
            "Today I {trigger}. {feeling}.",
            "{trigger}. {reaction}",
            "Nothing special: {trigger}. {emotion}",
            "{trigger}. {aftermath}",
        ],
    },
    "mental_health": {
        "triggers": [
            "intrusive thoughts won", "felt numb all day",
            "had a good day with no anxiety", "cried for no reason",
            "used my coping skills", "felt hopeful for the first time",
            "self-critical voice was loud", "journaling helped",
            "felt disconnected from my body", "had a flashback",
            "grounding techniques worked", "felt genuinely happy",
        ],
        "templates": [
            "Mental health update: {trigger}. {feeling}.",
            "{trigger}. {aftermath}",
            "Been struggling: {trigger}. {emotion}",
            "{trigger}. {reaction}",
        ],
    },
}

PERSONAS = [
    {"name": "alice", "age": 28, "job": "designer", "voice": ["I guess", "maybe", "idk"]},
    {"name": "bob", "age": 35, "job": "teacher", "voice": ["honestly", "to be fair", "still"]},
    {"name": "charlie", "age": 24, "job": "student", "voice": ["like", "ugh", "whatever"]},
    {"name": "diana", "age": 42, "job": "nurse", "voice": ["just", "actually", "as usual"]},
    {"name": "ethan", "age": 31, "job": "developer", "voice": ["well", "basically", "pretty"]},
]

EMOTION_WORDS = {
    "admiration": "admiring", "amusement": "amused", "anger": "angry",
    "annoyance": "annoyed", "approval": "appreciative", "caring": "caring",
    "confusion": "confused", "curiosity": "curious", "desire": "longing",
    "disappointment": "disappointed", "disapproval": "disapproving",
    "disgust": "disgusted", "embarrassment": "embarrassed",
    "excitement": "excited", "fear": "scared", "gratitude": "grateful",
    "grief": "grieving", "joy": "joyful", "love": "loving",
    "nervousness": "nervous", "optimism": "hopeful", "pride": "proud",
    "realization": "realizing", "relief": "relieved",
    "remorse": "remorseful", "sadness": "sad", "surprise": "surprised",
    "neutral": "neutral",
}

EMOTION_SUMMARIES = {
    "admiration": "Feeling inspired by someone's actions.",
    "amusement": "Light-hearted and entertained.",
    "anger": "Frustrated and irritable.",
    "annoyance": "Minor irritation, restless.",
    "approval": "Feeling validated and accepted.",
    "caring": "Warm and nurturing feelings.",
    "confusion": "Uncertain, mind foggy.",
    "curiosity": "Interested, wanting to know more.",
    "desire": "Longing for something or someone.",
    "disappointment": "Let down by expectations.",
    "disapproval": "Displeased with someone or something.",
    "disgust": "Repulsed or turned off.",
    "embarrassment": "Self-conscious, awkward.",
    "excitement": "Energetic and positive anticipation.",
    "fear": "Anxious, threatened, unsafe.",
    "gratitude": "Thankful and appreciative.",
    "grief": "Deep sadness over a loss.",
    "joy": "Light, happy, content.",
    "love": "Deep affection and connection.",
    "nervousness": "On edge, worried about outcomes.",
    "optimism": "Hopeful outlook about the future.",
    "pride": "Sense of accomplishment and self-worth.",
    "realization": "Sudden insight, something clicking.",
    "relief": "Tension released, exhaling.",
    "remorse": "Guilt, wishing to undo something.",
    "sadness": "Down, heavy-hearted, low energy.",
    "surprise": "Startled or caught off guard.",
    "neutral": "Even, balanced, nothing extreme.",
}

AUDIENCE_WORDS = ["I feel", "I'm feeling", "it's making me", "honestly I'm", "lowkey", "kind of", "really", "so"]
REACTION_FRAGMENTS = ["Not sure what to do with it.", "Trying to sit with it.", "Hope tomorrow is better.", "Just taking it one day at a time.", "Already feeling a bit better.", "This is going to take time.", "Glad I wrote this down.", "At least I tried."]
AFTERMATH_FRAGMENTS = ["Now I just need to decompress.", "Going to take a walk.", "Might call a friend.", "Time for some self-care.", "Gonna journal more about this.", "Need to talk to my therapist.", "Let's see what tomorrow brings.", "Cooking dinner to distract myself."]


def pick_emotions():
    count = random.choices([1, 2, 3], weights=[30, 50, 20])[0]
    emotions = random.sample(list(EMOTION_WORDS.keys()), count)
    if "neutral" in emotions and count > 1:
        emotions.remove("neutral")
    return emotions


def make_journal_entry(persona):
    category = random.choice(list(SCENARIOS.keys()))
    scenario = SCENARIOS[category]
    emotions = pick_emotions()
    trigger = random.choice(scenario["triggers"])
    template = random.choice(scenario["templates"])
    voice_word = random.choice(persona["voice"])
    audience = random.choice(AUDIENCE_WORDS)
    emotion_word = EMOTION_WORDS[emotions[0]]
    feeling = f"{audience} {emotion_word}"
    if len(emotions) > 1:
        feeling += f" and {EMOTION_WORDS[emotions[1]]}"
    reaction = random.choice(REACTION_FRAGMENTS)
    aftermath = random.choice(AFTERMATH_FRAGMENTS)

    raw = template.format(trigger=trigger, feeling=feeling, reaction=reaction, aftermath=aftermath, emotion=emotion_word, emotion_word=emotion_word)
    raw = raw[0].lower() + raw[1:] if raw[0].isupper() else raw
    raw = f"{voice_word.capitalize()}, {raw}"

    summary_parts = [EMOTION_SUMMARIES[e] for e in emotions]
    summary = " ".join(summary_parts)
    if category == "work":
        summary = "Work-related. " + summary
    elif category == "relationships":
        summary = "Interpersonal. " + summary
    elif category == "health":
        summary = "Health-focused. " + summary
    elif category == "mental_health":
        summary = "Therapeutic context. " + summary

    return {"raw_content": raw, "summary": summary, "emotions": emotions, "persona": persona["name"]}


def main():
    entries = []
    for i in range(500):
        persona = random.choice(PERSONAS)
        entry = make_journal_entry(persona)
        entries.append(entry)

    random.shuffle(entries)

    with open(OUT, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")

    emotion_counts = {}
    for e in entries:
        for em in e["emotions"]:
            emotion_counts[em] = emotion_counts.get(em, 0) + 1

    print(f"Generated {len(entries)} synthetic journal entries")
    print(f"Saved to {OUT}")
    print(f"\nEmotion distribution:")
    for em, count in sorted(emotion_counts.items(), key=lambda x: -x[1]):
        print(f"  {em}: {count}")
    print(f"\nPersona distribution:")
    for name in [p["name"] for p in PERSONAS]:
        count = sum(1 for e in entries if e["persona"] == name)
        print(f"  {name}: {count}")
    print(f"\nSample entries:")
    for e in entries[:5]:
        print(f"  [{e['persona']}] {e['raw_content'][:70]}... -> {e['summary']}")


if __name__ == "__main__":
    main()
