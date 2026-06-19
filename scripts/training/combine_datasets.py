import json
from pathlib import Path

HERE = Path(__file__).parent
GOEMOTIONS = HERE / "goemotions_instruction.jsonl"
JOURNAL_EMOTION = HERE / "journal_emotion_500.jsonl"
JOURNAL_SUMMARY = HERE / "journal_summary_500.jsonl"
REAL_SUMMARY = HERE / "journal_instruction.jsonl"
OUT_TRAIN = HERE / "sentinel_train.jsonl"


def main():
    lines = []

    # 1. GoEmotions — 58k emotion classification examples
    with open(GOEMOTIONS, encoding="utf-8") as f:
        for line in f:
            lines.append(json.loads(line))
    print(f"GoEmotions: {len(lines)} emotion tasks")

    # 2. Synthetic journal emotion — 500 journal-specific emotion tasks
    with open(JOURNAL_EMOTION, encoding="utf-8") as f:
        for line in f:
            lines.append(json.loads(line))
    print(f"Journal emotion: 500 emotion tasks")

    # 3. Synthetic journal summary — 500 empathetic analysis tasks
    with open(JOURNAL_SUMMARY, encoding="utf-8") as f:
        for line in f:
            lines.append(json.loads(line))
    print(f"Journal summary: 500 analysis tasks")

    # 4. Real journal summaries — 18 more
    with open(REAL_SUMMARY, encoding="utf-8") as f:
        for line in f:
            lines.append(json.loads(line))
    print(f"Real journal: 18 analysis tasks")

    # Shuffle
    import random
    random.shuffle(lines)

    with open(OUT_TRAIN, "w", encoding="utf-8") as f:
        for item in lines:
            f.write(json.dumps(item) + "\n")

    print(f"\nTotal training examples: {len(lines)}")
    print(f"Saved to: {OUT_TRAIN}")
    print(f"Size: {OUT_TRAIN.stat().st_size / 1e6:.1f} MB")

    # Show composition
    emotions = sum(1 for l in lines if "emotion" in l["instruction"].lower())
    analysis = sum(1 for l in lines if "analysis" in l["instruction"].lower())
    print(f"Emotion tasks: {emotions}, Analysis tasks: {analysis}")


if __name__ == "__main__":
    main()
