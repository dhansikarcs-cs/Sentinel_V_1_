"""Train the GoEmotions classifier on the REAL GoEmotions dataset."""

import os
import sys
import time

import joblib
import numpy as np
from datasets import load_dataset
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.multiclass import OneVsRestClassifier

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "emotion_model_real.joblib")


def load_goemotions():
    """Load the real GoEmotions dataset from Hugging Face."""
    print("Loading GoEmotions dataset from Hugging Face...")
    ds = load_dataset("google-research-datasets/go_emotions", "simplified")

    # The 'simplified' config has 28 labels (27 emotions + neutral)
    # Each example has 'text' and 'labels' (list of integer label indices)
    texts = []
    labels = []

    for split in ["train", "validation", "test"]:
        for example in ds[split]:
            text = example["text"]
            label_indices = example["labels"]
            # Convert to multi-hot vector
            label_vec = [0] * 28
            for idx in label_indices:
                if idx < 28:
                    label_vec[idx] = 1
            texts.append(text)
            labels.append(label_vec)

    print(f"Loaded {len(texts)} examples")
    labels_arr = np.array(labels, dtype=np.float32)
    labels_arr = np.ascontiguousarray(labels_arr)
    return texts, labels_arr


def train_model(texts, labels):
    """Train TF-IDF + LogisticRegression on real GoEmotions data."""
    print("Splitting data 80/20...")
    x_train, x_test, y_train, y_test = train_test_split(texts, labels, test_size=0.2, random_state=42)
    print(f"Train: {len(x_train)}, Test: {len(x_test)}")

    print("Building TF-IDF vectorizer...")
    vectorizer = TfidfVectorizer(
        max_features=10000,
        ngram_range=(1, 3),
        sublinear_tf=True,
        lowercase=True,
        strip_accents="unicode",
        token_pattern=r"(?u)\b\w+\b",
        min_df=2,
        max_df=0.95,
    )

    print("Transforming texts...")
    x_train_tfidf = vectorizer.fit_transform(x_train).copy()
    x_test_tfidf = vectorizer.transform(x_test).copy()
    print(f"TF-IDF features: {x_train_tfidf.shape[1]}")

    print("Training OneVsRest LogisticRegression (this takes a minute)...")
    t0 = time.time()
    classifier = OneVsRestClassifier(
        LogisticRegression(
            C=2.0,
            class_weight="balanced",
            max_iter=1000,
            solver="liblinear",
        ),
        n_jobs=1,
    )
    classifier.fit(x_train_tfidf, y_train)
    train_time = time.time() - t0
    print(f"Training completed in {train_time:.1f}s")

    # Evaluate on test set
    print("\nEvaluating on test set...")
    y_pred = classifier.predict(x_test_tfidf)

    # Per-emotion metrics
    print("\n=== Per-Emotion Results ===")
    report = classification_report(
        y_test,
        y_pred,
        target_names=GOEMOTIONS,
        zero_division=0,
    )
    print(report)

    # Overall metrics
    micro_f1 = f1_score(y_test, y_pred, average="micro", zero_division=0)
    macro_f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)
    samples_f1 = f1_score(y_test, y_pred, average="samples", zero_division=0)
    print(f"Micro F1:  {micro_f1:.4f}")
    print(f"Macro F1:  {macro_f1:.4f}")
    print(f"Samples F1: {samples_f1:.4f}")

    return (
        classifier,
        vectorizer,
        {
            "micro_f1": micro_f1,
            "macro_f1": macro_f1,
            "samples_f1": samples_f1,
            "train_size": len(x_train),
            "test_size": len(x_test),
            "train_time_s": train_time,
            "n_features": x_train_tfidf.shape[1],
        },
    )


def save_model(classifier, vectorizer, metrics):
    """Save trained model and print summary."""
    joblib.dump(
        {"classifier": classifier, "vectorizer": vectorizer, "emotions": GOEMOTIONS},
        MODEL_PATH,
    )
    size_kb = os.path.getsize(MODEL_PATH) / 1024
    print(f"\nModel saved to {MODEL_PATH}")
    print(f"Model size: {size_kb:.1f} KB")
    print("\n=== Summary ===")
    print("Dataset: GoEmotions (real, from Google Research via Hugging Face)")
    print(f"Examples: {metrics['train_size']} train, {metrics['test_size']} test")
    print(f"Features: {metrics['n_features']} TF-IDF features")
    print(f"Training time: {metrics['train_time_s']:.1f}s")
    print(f"Micro F1: {metrics['micro_f1']:.4f}")
    print(f"Macro F1: {metrics['macro_f1']:.4f}")
    print(f"Samples F1: {metrics['samples_f1']:.4f}")


if __name__ == "__main__":
    texts, labels = load_goemotions()
    classifier, vectorizer, metrics = train_model(texts, labels)
    save_model(classifier, vectorizer, metrics)
