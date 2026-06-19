import json
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "software" / "data" / "history_archive.json"
OUT = Path(__file__).parent / "journal_instruction.jsonl"


def main():
    with open(SRC, encoding="utf-8") as f:
        archive = json.load(f)

    entries = []
    for user, user_entries in archive.items():
        for e in user_entries:
            text = e.get("raw_content", "").strip()
            summary = e.get("summary", "").strip()
            if text.startswith("gAAAAAB"):
                continue
            if not text or not summary or len(text) < 5:
                continue
            entries.append({"user": user, "text": text, "summary": summary})

    print(f"Total usable journal entries: {len(entries)}")

    for e in entries:
        print(f"  [{e['user']}] {e['text'][:60]}... -> {e['summary']}")

    with open(OUT, "w", encoding="utf-8") as f:
        for e in entries:
            entry = {
                "instruction": "Read this journal entry and write an empathetic, human-sounding analysis. "
                               "Be warm, specific to what they wrote, and acknowledge their feelings naturally. "
                               "Keep it 1-3 sentences.",
                "input": e["text"],
                "output": e["summary"],
            }
            f.write(json.dumps(entry) + "\n")

    print(f"Saved to {OUT}")


if __name__ == "__main__":
    main()
