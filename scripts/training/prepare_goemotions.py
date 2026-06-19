import csv
import json
import random
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "software" / "data" / "rnd" / "goemotions_clean.csv"
OUT = Path(__file__).parent / "goemotions_instruction.jsonl"
SAMPLE = Path(__file__).parent / "goemotions_sample_2000.jsonl"

EMOTION_COLS = [
    "admiration","amusement","anger","annoyance","approval","caring","confusion",
    "curiosity","desire","disappointment","disapproval","disgust","embarrassment",
    "excitement","fear","gratitude","grief","joy","love","nervousness","optimism",
    "pride","realization","relief","remorse","sadness","surprise","neutral",
]

def get_emotions(row):
    return [c for c in EMOTION_COLS if row[c] == "1"]

def main():
    rows = []
    with open(SRC, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = row["text"].strip()
            if not text or len(text) < 3:
                continue
            emotions = get_emotions(row)
            if not emotions:
                continue
            rows.append({"text": text, "emotions": emotions})

    print(f"Total valid rows: {len(rows)}")

    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows:
            entry = {
                "instruction": "Analyze the emotion in this text. Respond with the emotion labels that apply.",
                "input": r["text"],
                "output": ", ".join(r["emotions"]),
            }
            f.write(json.dumps(entry) + "\n")

    sample = random.sample(rows, min(2000, len(rows)))
    with open(SAMPLE, "w", encoding="utf-8") as f:
        for r in sample:
            entry = {
                "instruction": "Analyze the emotion in this text. Respond with the emotion labels that apply.",
                "input": r["text"],
                "output": ", ".join(r["emotions"]),
            }
            f.write(json.dumps(entry) + "\n")

    print(f"Full dataset: {OUT} ({len(rows)} examples)")
    print(f"Sample dataset: {SAMPLE} ({len(sample)} examples — quick test)")
    print(f"Distinct emotion combos: {len(set(','.join(r['emotions']) for r in rows))}")


if __name__ == "__main__":
    main()
