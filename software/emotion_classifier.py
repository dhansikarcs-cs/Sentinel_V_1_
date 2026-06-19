import pickle, re
from pathlib import Path

MODEL_PATH = Path(__file__).parent / "models" / "emotion_tfidf.pkl"

EMOTIONS = [
    "admiration","amusement","anger","annoyance","approval","caring","confusion",
    "curiosity","desire","disappointment","disapproval","disgust","embarrassment",
    "excitement","fear","gratitude","grief","joy","love","nervousness","optimism",
    "pride","realization","relief","remorse","sadness","surprise","neutral",
]

_pipe = None


def _load():
    global _pipe
    if _pipe is not None:
        return
    if not MODEL_PATH.exists():
        return
    with open(MODEL_PATH, "rb") as f:
        _pipe = pickle.load(f)


def classify_text(text: str, threshold: float = 0.2) -> str:
    _load()
    if _pipe is None:
        return ""
    cleaned = re.sub(r"\s+", " ", re.sub(r"[^a-z\s]", " ", str(text).lower())).strip()
    if not cleaned:
        return ""
    probs = _pipe.predict_proba([cleaned])
    labels = [EMOTIONS[i] for i, p in enumerate(probs[0]) if p > threshold]
    if not labels:
        return ""
    if "neutral" in labels and len(labels) > 1:
        labels.remove("neutral")
    return ", ".join(labels)
