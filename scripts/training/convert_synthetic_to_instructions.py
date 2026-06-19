import json
from pathlib import Path

HERE = Path(__file__).parent
SYNTHETIC = HERE / "journal_synthetic_500.jsonl"
REAL_ENTRIES = HERE / "journal_instruction.jsonl"
OUT_EMOTION = HERE / "journal_emotion_500.jsonl"
OUT_SUMMARY = HERE / "journal_summary_500.jsonl"

POSITIVE_EMOTIONS = {
    "admiration","amusement","approval","caring","curiosity","excitement",
    "gratitude","joy","love","optimism","pride","relief","surprise",
}
NEGATIVE_EMOTIONS = {
    "anger","annoyance","confusion","desire","disappointment","disapproval",
    "disgust","embarrassment","fear","grief","nervousness","remorse","sadness",
}

def main():
    # Load synthetic entries
    syn_entries = []
    with open(SYNTHETIC, encoding="utf-8") as f:
        for line in f:
            syn_entries.append(json.loads(line))
    print(f"Synthetic entries: {len(syn_entries)}")

    # Convert synthetic entries to emotion instruction format
    with open(OUT_EMOTION, "w", encoding="utf-8") as f:
        for e in syn_entries:
            entry = {
                "instruction": "Analyze the emotion in this journal entry. Respond with the emotion labels that apply.",
                "input": e["raw_content"],
                "output": ", ".join(e["emotions"]),
            }
            f.write(json.dumps(entry) + "\n")

    # Convert synthetic entries to summary instruction format
    with open(OUT_SUMMARY, "w", encoding="utf-8") as f:
        for e in syn_entries:
            raw = e["raw_content"]
            summary = e["summary"]
            # Add real ones too
            entry = {
                "instruction": "Read this journal entry and write an empathetic, human-sounding analysis. "
                               "Be warm, specific to what they wrote, and acknowledge their feelings naturally. "
                               "Keep it 1-3 sentences.",
                "input": raw,
                "output": summary,
            }
            f.write(json.dumps(entry) + "\n")

    print(f"Emotion instructions: {OUT_EMOTION}")
    print(f"Summary instructions: {OUT_SUMMARY}")

    # Show sample
    with open(OUT_SUMMARY, encoding="utf-8") as f:
        samples = [json.loads(f.readline()) for _ in range(3)]
    print("\nSample summary entries:")
    for s in samples:
        print(f"  Input: {s['input'][:60]}...")
        print(f"  Output: {s['output']}")
        print()


if __name__ == "__main__":
    main()
