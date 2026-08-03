from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Sentinel AI Service", version="1.0.0")


class ClassifyRequest(BaseModel):
    text: str
    threshold: float = 0.15


class ClassifyResponse(BaseModel):
    emotions: list[str]
    probabilities: dict[str, float]


class RiskRequest(BaseModel):
    text: str
    emotion_probs: dict[str, float] | None = None


class RiskResponse(BaseModel):
    risk_score: int
    triggered: bool
    reasoning: str
    emotions: str
    explainability: dict


@app.get("/health")
def health():
    return {"status": "ok", "service": "ai"}


@app.post("/classify", response_model=ClassifyResponse)
def classify(req: ClassifyRequest):
    import sys
    sys.path.insert(0, "..")
    from app.ml.emotion_classifier import EmotionClassifier
    clf = EmotionClassifier()
    probs = clf.predict_proba(req.text)
    top = clf.predict_top(req.text, threshold=req.threshold)
    return ClassifyResponse(
        emotions=[e for e, p in top if e != "neutral"],
        probabilities=probs,
    )


@app.post("/risk", response_model=RiskResponse)
def assess_risk(req: RiskRequest):
    import sys
    sys.path.insert(0, "..")
    from app.ml.risk_engine import assess_risk_with_explainability
    result = assess_risk_with_explainability(req.text, req.emotion_probs)
    return RiskResponse(**result)
