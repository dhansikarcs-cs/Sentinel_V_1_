"""Train the GoEmotions classifier on the REAL GoEmotions dataset.

IMPORTANT (audit fix, Aug 2026): earlier versions merged the official
train/validation/test splits and then took a random 80/20 split from the whole
pool. That leaked ~4,346 of the 5,427 official test rows into the training
partition, which inflated any subsequently-reported official-test numbers.
This version TRAINS on the official train+validation splits ONLY and reserves
the official test split exclusively for evaluation (no leakage).
"""

import os
import sys
import time

import joblib
import numpy as np
from datasets import load_dataset
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
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
    """Load the real GoEmotions dataset from Hugging Face (no leakage).

    Returns (train_texts, train_labels, test_texts, test_labels) where the
    train pool = official train + validation splits and test = official test.
    """
    print("Loading GoEmotions dataset from Hugging Face...")
    ds = load_dataset("google-research-datasets/go_emotions", "simplified")

    def to_arrays(split):
        texts, labels = [], []
        for example in ds[split]:
            label_vec = [0] * 28
            for idx in example["labels"]:
                if idx < 28:
                    label_vec[idx] = 1
            texts.append(example["text"])
            labels.append(label_vec)
        return texts, np.array(labels, dtype=np.float32)

    train_texts, train_labels = to_arrays("train")
    val_texts, val_labels = to_arrays("validation")
    test_texts, test_labels = to_arrays("test")

    # training pool = official train + official validation (never the test split)
    train_texts = train_texts + val_texts
    train_labels = np.vstack([train_labels, val_labels])
    train_labels = np.ascontiguousarray(train_labels)

    print(f"Loaded {len(train_texts)} train examples (+official val), {len(test_texts)} official test examples")
    print(f"train shape={train_labels.shape} test shape={test_labels.shape}")
    return train_texts, train_labels, test_texts, test_labels


def train_model(x_train, y_train, x_test, y_test):
    """Train TF-IDF + LogisticRegression on real GoEmotions data."""
    print("Splitting data (train+val -> fit, official test -> eval)...")
    print(f"Train: {len(x_train)}, Test (official, held out): {len(x_test)}")

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

    # Evaluate on official test set (never seen by the model)
    print("\nEvaluating on official held-out test set (no leakage)...")
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
    print(f"Examples: {metrics['train_size']} train, {metrics['test_size']} test (official, no leakage)")
    print(f"Features: {metrics['n_features']} TF-IDF features")
    print(f"Training time: {metrics['train_time_s']:.1f}s")
    print(f"Micro F1: {metrics['micro_f1']:.4f}")
    print(f"Macro F1: {metrics['macro_f1']:.4f}")
    print(f"Samples F1: {metrics['samples_f1']:.4f}")


if __name__ == "__main__":
    train_texts, train_labels, test_texts, test_labels = load_goemotions()
    classifier, vectorizer, metrics = train_model(train_texts, train_labels, test_texts, test_labels)
    save_model(classifier, vectorizer, metrics)
