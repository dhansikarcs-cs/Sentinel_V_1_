import os
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier

GOEMOTIONS = [
    "admiration",
    "amusement",
    "anger",
    "annoyance",
    "approval",
    "caring",
    "confusion",
    "curiosity",
    "desire",
    "disappointment",
    "disapproval",
    "disgust",
    "embarrassment",
    "excitement",
    "fear",
    "gratitude",
    "grief",
    "joy",
    "love",
    "nervousness",
    "optimism",
    "pride",
    "realization",
    "relief",
    "remorse",
    "sadness",
    "surprise",
    "neutral",
]

EMOTION_KEYWORDS: dict[str, list[str]] = {
    "admiration": ["admire", "inspired", "proud of", "respect", "look up to"],
    "amusement": ["funny", "hilarious", "amusing", "made me laugh", "humor"],
    "anger": ["angry", "furious", "rage", "mad", "pissed off", "infuriated"],
    "annoyance": ["annoyed", "irritated", "frustrated", "aggravated", "bugging me"],
    "approval": ["approve", "good job", "well done", "proud", "pleased with"],
    "caring": ["care about", "concerned", "worried about you", "take care", "nurture"],
    "confusion": ["confused", "don't understand", "unclear", "perplexed", "lost"],
    "curiosity": ["curious", "wonder", "what if", "interested", "tell me more"],
    "desire": ["want", "wish", "desire", "long for", "crave", "yearn"],
    "disappointment": ["disappointed", "let down", "failed", "not what i expected"],
    "disapproval": ["disapprove", "bad idea", "wrong", "shouldn't", "not good"],
    "disgust": ["disgusting", "gross", "repulsed", "revolting", "sickening"],
    "embarrassment": ["embarrassed", "awkward", "humiliated", "shame", "mortified"],
    "excitement": ["excited", "thrilled", "can't wait", "looking forward", "amazing"],
    "fear": ["scared", "afraid", "terrified", "fear", "panic", "anxious", "dread"],
    "gratitude": ["grateful", "thankful", "appreciate", "blessed", "thank you"],
    "grief": ["grief", "mourning", "loss", "miss them", "passed away", "bereaved"],
    "joy": ["joy", "happy", "delighted", "wonderful", "beautiful", "fantastic"],
    "love": ["love", "adore", "cherish", "beloved", "dear"],
    "nervousness": ["nervous", "anxious", "worried", "uneasy", "restless", "tense"],
    "optimism": ["optimistic", "hopeful", "positive", "looking up", "bright future"],
    "pride": ["proud", "accomplished", "achievement", "milestone", "congratulate"],
    "realization": ["realize", "understand now", "it clicked", "epiphany", "aware"],
    "relief": ["relieved", "finally", "thank goodness", "weight off", "at ease"],
    "remorse": ["sorry", "regret", "apologize", "remorse", "guilty", "shouldn't have"],
    "sadness": ["sad", "depressed", "heartbroken", "lonely", "crying", "miserable"],
    "surprise": ["surprised", "shocked", "unexpected", "astonished", "amazed"],
    "neutral": [],
}

MODEL_PATH = Path(__file__).parent / "emotion_model.pkl"


def _generate_training_data() -> tuple[list[str], list[list[int]]]:
    texts: list[str] = []
    labels: list[list[int]] = []

    base_templates = [
        "I feel {}",
        "I am {}",
        "I'm feeling {}",
        "This is {}",
        "Everything feels {}",
        "I am so {}",
        "I feel so {}",
        "It makes me {}",
        "I've been feeling {}",
        "Today I feel {}",
    ]

    crisis_emotion_templates = {
        "fear": [
            "I am terrified of what might happen next",
            "My heart races when I think about the future",
            "I feel a deep sense of dread that won't go away",
            "Every sound makes me jump, I feel constantly on edge",
            "I'm afraid to be alone, the thoughts consume me",
            "The anxiety is paralyzing, I can't function normally",
            "I fear I'm losing control of my own mind",
            "What if everything falls apart, I can't stop thinking about it",
            "The panic attacks are getting worse, I'm scared",
            "I feel trapped and frightened with no way out",
            "My chest tightens every time I hear bad news",
            "I'm dreading tomorrow, I don't know how to face it",
            "The world feels dangerous and unpredictable",
            "I feel like something terrible is about to happen",
            "I can't shake this feeling of impending doom",
            "Every decision fills me with paralyzing fear",
            "I'm scared to tell anyone how I really feel",
            "The fear keeps me awake at night, staring at the ceiling",
            "I avoid everything because I'm afraid of failing",
            "Social situations make me incredibly anxious and fearful",
            "I'm frightened by my own thoughts sometimes",
            "The phobia is getting worse, I can barely leave home",
            "I feel a constant knot of fear in my stomach",
            "I'm terrified of being judged by everyone around me",
            "Worry consumes my every waking moment",
            "I feel unsafe even in my own home",
            "My mind races with worst-case scenarios constantly",
        ],
        "sadness": [
            "I feel a deep emptiness that nothing seems to fill",
            "Tears come without warning, I can't stop them",
            "Everything feels gray and meaningless",
            "I miss who I used to be before all this",
            "The weight of sadness is crushing me",
            "I cried myself to sleep again last night",
            "Nothing brings me joy anymore, everything feels flat",
            "I feel like I'm drowning in my own sorrow",
            "The grief hasn't gotten easier, it just keeps coming",
            "I isolate myself because I don't want to burden others",
            "My heart feels heavy, like it's carrying the world",
            "I can barely get out of bed, what's the point",
            "The sadness is constant, like a cloud that never lifts",
            "I feel broken in a way that can't be fixed",
            "Every song sounds like a sad song these days",
            "I look in the mirror and don't recognize the person staring back",
            "The loneliness is deafening, even in a crowded room",
            "I pretend to be okay but inside I'm falling apart",
            "I've lost interest in everything I used to love",
            "The pain is unbearable but I keep smiling for everyone",
            "I feel like I'm invisible, like I don't matter",
            "There's an ache in my chest that never goes away",
            "I feel completely hopeless about the future",
            "Even small tasks feel impossible when I'm this sad",
            "I wish someone would notice how much I'm struggling",
            "The tears flow silently, no one sees them",
            "I feel empty, like a shell of who I used to be",
        ],
        "grief": [
            "I still reach for my phone to call them, then remember",
            "The house feels so empty without them",
            "I talk to them even though they can't hear me",
            "Grief hits in waves, sometimes I can barely breathe",
            "I see their face in every crowd, hoping it's them",
            "The silence where their voice used to be is deafening",
            "I keep their things exactly as they left them",
            "Some days I forget for a moment, then the pain crashes back",
            "I'm grieving someone who is still alive but gone from my life",
            "The anniversary makes everything feel fresh again",
            "I feel guilty for laughing, like I'm betraying their memory",
            "I search for signs of them everywhere I go",
            "Nothing will ever be the same without them",
            "I replay our last conversation over and over",
            "The world moved on but I'm stuck in this moment",
            "I carry this loss like a stone in my chest",
            "I dream about them and wake up thinking they're here",
            "Grief is love with nowhere to go",
            "I miss the little things the most, the way they said my name",
            "I feel guilty for the things I never said",
            "They took a piece of me when they left",
            "I try to honor their memory by living but it's hard",
            "The pain of absence is worse than any physical wound",
            "I feel like I'll never be whole again",
            "Every happy moment is tinged with the sadness of their absence",
            "I would give anything for one more day with them",
            "The grief has changed me permanently",
        ],
        "anger": [
            "I'm so frustrated I could scream",
            "The rage inside me is barely contained",
            "I feel a burning anger that won't dissipate",
            "Everything makes me irritable and on edge",
            "I want to break something, anything to release this",
            "The injustice makes my blood boil",
            "I'm angry at the world and everyone in it",
            "My temper is getting shorter every day",
            "I feel this deep resentment building inside me",
            "They had no right to treat me that way",
            "I clench my fists thinking about what they did",
            "The anger is eating me alive from the inside",
            "I fantasize about telling everyone exactly what I think",
            "I'm furious at myself for letting things get this bad",
            "The frustration is overwhelming, nothing goes right",
            "I want to lash out but I know it won't help",
            "I feel like punching a wall, the anger is physical",
            "I'm seething with barely controlled rage",
            "The betrayal cut deep and I can't forgive",
            "I'm angry at myself for being so weak",
            "My blood boils when I think about the unfairness",
            "I feel this hot anger rising in my chest",
            "I'm tired of being pushed around by everyone",
            "The rage comes in waves, each one stronger than the last",
            "I want to break free from this anger but it consumes me",
            "I'm so mad I can barely think straight",
            "The bitterness is poisoning everything around me",
        ],
        "admiration": [
            "She inspires me to be a better person every day",
            "I look up to my mentor more than anyone",
            "The way she handled that situation was incredible",
            "I'm in awe of their dedication and talent",
            "They set the perfect example for all of us",
            "I admire how they never give up no matter what",
            "Their strength and courage inspire me deeply",
            "I respect them more than words can express",
            "Watching them work is truly motivating",
            "They are the role model I always needed",
            "I'm inspired by everything they've accomplished",
            "The way they treat people with such kindness is admirable",
            "I aspire to be half the person they are",
            "Their perseverance through hardship amazes me",
            "I have the deepest respect for what they do",
            "They handle pressure with such grace and skill",
            "I look up to them for their integrity",
            "Their passion for their work is truly inspiring",
            "I'm constantly impressed by their abilities",
            "They make everyone around them want to do better",
            "I admire their courage to speak the truth",
            "The impact they've had on my life is immeasurable",
            "I'm grateful to have someone like them to look up to",
            "Their commitment to helping others is admirable",
            "I hold them in the highest regard",
            "I'm blessed to know someone so remarkable",
            "They represent everything I want to be",
        ],
        "amusement": [
            "That joke was absolutely hilarious",
            "I couldn't stop laughing at that comedy show",
            "The way they told that story was so funny",
            "I was cracking up the entire time",
            "That meme perfectly captures how I feel",
            "My friend's prank had me in stitches",
            "I laughed so hard my sides hurt",
            "That movie had me rolling on the floor laughing",
            "The punchline caught me completely off guard",
            "I haven't laughed that hard in ages",
            "The absurdity of the situation is almost comical",
            "My cat does the funniest things every day",
            "I found the humor in a really dark situation",
            "That comedy special was pure gold",
            "The contrast between expectation and reality was hilarious",
            "I shared the funniest joke with my coworkers today",
            "Watching bloopers is my favorite way to relax",
            "The kids said the most hilarious thing at dinner",
            "I appreciate good comedy more than anything",
            "The sarcasm in that comment was brilliant",
            "That stand-up comedian really knows how to read a room",
            "I'm still chuckling about what happened earlier",
            "The timing of that joke was absolutely perfect",
            "Something so simple had me laughing for minutes",
            "I can't believe how funny that accident turned out to be",
            "The whole situation was absurdly comical",
            "I needed that laugh more than anything",
        ],
        "excitement": [
            "I can't wait for the concert next week",
            "I'm thrilled about starting this new project",
            "The anticipation is killing me in the best way",
            "I just got the best news of my life",
            "I'm buzzing with energy and excitement",
            "This opportunity could change everything for me",
            "I'm counting down the days until the trip",
            "My heart is racing with anticipation",
            "I'm so pumped about what's coming next",
            "The excitement is almost too much to contain",
            "I've been looking forward to this all year",
            "I feel electric with possibility",
            "I just booked the vacation of a lifetime",
            "My promotion was confirmed today and I'm ecstatic",
            "I'm jumping for joy right now",
            "The news couldn't have come at a better time",
            "I feel alive with new energy and purpose",
            "Something amazing is about to happen and I know it",
            "I'm absolutely giddy about this surprise",
            "The energy in the room is infectious",
            "I've never felt this level of enthusiasm before",
            "I'm over the moon about this achievement",
            "The wait is finally over, I'm so excited",
            "I want to scream with joy from the rooftops",
            "Everything is falling into place and it feels incredible",
            "I'm vibrating with positive energy",
            "This is going to be the best day ever",
        ],
        "joy": [
            "I am so happy right now, nothing could ruin this moment",
            "My heart is overflowing with happiness",
            "Today was one of the best days of my life",
            "I feel pure, unadulterated joy",
            "The smile on my face won't go away",
            "I'm radiating happiness and everyone can see it",
            "This moment of bliss is everything I needed",
            "I'm savoring every second of this wonderful feeling",
            "Happiness like this makes everything worth it",
            "I feel like the luckiest person alive right now",
            "The world looks brighter when you're happy",
            "I can't stop smiling, I'm so delighted",
            "This joy is infectious, spreading to everyone around me",
            "I finally feel the happiness I've been searching for",
            "My soul is dancing with pure delight",
            "Every cell in my body feels happy",
            "I'm overwhelmed with a beautiful sense of joy",
            "The happiness in my heart is boundless",
            "I feel completely content and at peace with the world",
            "Today I woke up with a heart full of joy",
            "This moment is pure magic and I'm soaking it in",
            "I'm floating on a cloud of happiness",
            "The joy I feel is immeasurable",
            "I've discovered what true happiness feels like",
            "I feel blessed beyond measure",
            "My joy is uncontainable and contagious",
            "I'm living my best life and it feels amazing",
        ],
        "love": [
            "I love them with every fiber of my being",
            "My heart belongs to someone special",
            "The way they look at me makes my heart flutter",
            "I feel a deep connection that goes beyond words",
            "Being with them feels like coming home",
            "I cherish every moment we spend together",
            "My love for them grows stronger every day",
            "They complete me in ways I never imagined possible",
            "I would do anything for the person I love",
            "The warmth of their embrace heals my soul",
            "I'm head over heels in love and it's wonderful",
            "They are the missing piece I've been searching for",
            "My heart skips a beat whenever they're near",
            "I feel so loved and cherished by this person",
            "Loving them is the easiest and most natural thing",
            "They make my world a more beautiful place",
            "I'm grateful for the love we share every day",
            "The bond we have is unbreakable and precious",
            "I can't imagine my life without them in it",
            "They bring out the best version of me",
            "My love is deep, endless, and unconditional",
            "Being in love feels like floating on air",
            "They are my everything, my reason for smiling",
            "I treasure our love more than anything in this world",
            "The depth of my love for them is infinite",
            "They are the love of my life, my soulmate",
            "I fall in love with them a little more every day",
        ],
        "optimism": [
            "I truly believe the best is yet to come",
            "Things are looking up and I'm hopeful about the future",
            "I have a positive outlook on everything ahead",
            "The future feels bright and full of promise",
            "I know this困难 will pass and better days are coming",
            "I'm confident that things will work out in the end",
            "Every sunrise brings new opportunities for growth",
            "I choose to see the good in every situation",
            "My glass is half full and overflowing with possibility",
            "I have faith that everything happens for a reason",
            "The road ahead is full of promise and potential",
            "I'm hopeful that my dreams will become reality",
            "Challenges are just opportunities in disguise",
            "I wake up each day knowing it will be a good one",
            "My positive mindset attracts positive outcomes",
            "I believe in my ability to overcome any obstacle",
            "The seeds I'm planting today will bloom beautifully tomorrow",
            "I'm optimistic about what the future holds for me",
            "There's always a silver lining if you look for it",
            "I trust that the universe has good things in store",
            "Every setback is setting me up for an even bigger comeback",
            "I feel hopeful and energized about what's to come",
            "The light at the end of the tunnel is getting brighter",
            "I'm excited about the possibilities that await me",
            "My positive attitude is my greatest strength",
            "I choose hope over fear every single time",
            "I have complete faith that everything will be okay",
        ],
        "neutral": [
            "I went to the store today",
            "The weather is nice",
            "I had lunch with a friend",
            "I watched a movie",
            "Nothing much happened",
            "It was an ordinary day",
            "I did my usual routine",
            "Work was fine",
            "I read a book",
            "I went for a walk",
            "The traffic was normal this morning",
            "I made dinner and watched television",
            "I need to buy groceries this weekend",
            "The meeting lasted about an hour",
            "I took the bus to work today",
            "My neighbor waved at me this morning",
            "I organized my desk at work",
            "The package arrived on time",
            "I watered the plants in the garden",
            "I finished reading the article I started yesterday",
            "The store was moderately busy",
            "I called my mother for a few minutes",
            "I went to the gym for an hour",
            "The library had the book I was looking for",
            "I paid my bills online today",
            "The commute was about thirty minutes",
            "I replied to some emails this afternoon",
            "The restaurant was fully booked",
            "I cleaned the kitchen after dinner",
            "I saw a documentary about history",
        ],
    }

    for emotion in GOEMOTIONS:
        if emotion == "neutral":
            continue
        keywords = EMOTION_KEYWORDS.get(emotion, [])
        if keywords:
            for kw in keywords:
                for t in base_templates:
                    sentence = t.format(kw)
                    texts.append(sentence)
                    lbl = [0] * len(GOEMOTIONS)
                    lbl[GOEMOTIONS.index(emotion)] = 1
                    labels.append(lbl)
        if emotion in crisis_emotion_templates:
            for sentence in crisis_emotion_templates[emotion]:
                texts.append(sentence)
                lbl = [0] * len(GOEMOTIONS)
                lbl[GOEMOTIONS.index(emotion)] = 1
                labels.append(lbl)

    neutral_templates = crisis_emotion_templates.get("neutral", [])
    for t in neutral_templates:
        texts.append(t)
        lbl = [0] * len(GOEMOTIONS)
        lbl[GOEMOTIONS.index("neutral")] = 1
        labels.append(lbl)

    return texts, np.array(labels, dtype=np.float32)


def _build_model() -> OneVsRestClassifier:
    texts, labels = _generate_training_data()
    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 3),
        sublinear_tf=True,
        lowercase=True,
        strip_accents="unicode",
        token_pattern=r"(?u)\b\w+\b",
    )
    X = vectorizer.fit_transform(texts)  # noqa: N806
    classifier = OneVsRestClassifier(
        LogisticRegression(C=2.0, class_weight="balanced", max_iter=1000, solver="liblinear"),
        n_jobs=-1,
    )
    classifier.fit(X, labels)
    return classifier, vectorizer


def train_and_save(path: str | Path = MODEL_PATH) -> None:
    classifier, vectorizer = _build_model()
    joblib.dump({"classifier": classifier, "vectorizer": vectorizer, "emotions": GOEMOTIONS}, path)
    print(f"Model saved to {path}")


class EmotionClassifier:
    def __init__(self, path: str | Path = MODEL_PATH):
        if not os.path.exists(path):
            train_and_save(path)
        data = joblib.load(path)
        self.classifier: OneVsRestClassifier = data["classifier"]
        self.vectorizer: TfidfVectorizer = data["vectorizer"]
        self.emotions: list[str] = data["emotions"]

    def predict_proba(self, text: str) -> dict[str, float]:
        X = self.vectorizer.transform([text])  # noqa: N806
        probs = self.classifier.predict_proba(X)
        result = {}
        sample = probs[0]
        for i, emotion in enumerate(self.emotions):
            result[emotion] = round(float(sample[i]), 4)
        return result

    def predict_top(self, text: str, threshold: float = 0.15, max_results: int = 5) -> list[tuple[str, float]]:
        probs = self.predict_proba(text)
        sorted_emotions = sorted(probs.items(), key=lambda x: x[1], reverse=True)
        filtered = [(e, p) for e, p in sorted_emotions if p >= threshold]
        if not filtered:
            return [("neutral", 1.0)]
        return filtered[:max_results]

    def predict_labels(self, text: str, threshold: float = 0.15) -> list[str]:
        return [e for e, p in self.predict_top(text, threshold=threshold)]


classifier = EmotionClassifier()
