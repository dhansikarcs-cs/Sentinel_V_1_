import csv, pickle, re, sys
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import Pipeline

SRC = Path(__file__).resolve().parents[2] / "software" / "data" / "rnd" / "goemotions_clean.csv"
OUT_DIR = Path(__file__).resolve().parents[2] / "software" / "models"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "emotion_tfidf.pkl"

EMOTIONS = [
    "admiration","amusement","anger","annoyance","approval","caring","confusion",
    "curiosity","desire","disappointment","disapproval","disgust","embarrassment",
    "excitement","fear","gratitude","grief","joy","love","nervousness","optimism",
    "pride","realization","relief","remorse","sadness","surprise","neutral",
]


def _clean(text):
    text = text.lower()
    text = re.sub(r"[^a-z\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def main():
    texts, labels = [], []
    with open(SRC, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = row["text"].strip()
            if not t or len(t) < 2:
                continue
            texts.append(_clean(t))
            labels.append([int(row[em]) for em in EMOTIONS])

    print(f"Loaded {len(texts)} examples, {len(EMOTIONS)} labels")

    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(max_features=15000, ngram_range=(1, 2), stop_words="english")),
        ("clf", OneVsRestClassifier(LogisticRegression(max_iter=1000, C=1.0))),
    ])

    print("Training...")
    pipe.fit(texts, labels)
    print("Done training.")

    with open(OUT, "wb") as f:
        pickle.dump(pipe, f)
    print(f"Model saved to {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")

    tests = [
        "That game hurt.",
        "I'm so excited! I got the job!",
        "My cat died today. I don't know what to do with myself.",
        "Feeling okay today. Nothing special.",
        "Work was stressful today. My manager criticized my report.",
    ]
    for t in tests:
        probs = pipe.predict_proba([_clean(t)])
        preds = []
        for i, em in enumerate(EMOTIONS):
            if probs[i][0][1] > 0.3:
                preds.append(em)
        print(f"  \"{t}\" -> {preds if preds else ['neutral']}")


if __name__ == "__main__":
    main()
