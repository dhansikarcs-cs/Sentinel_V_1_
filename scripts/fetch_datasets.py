"""Fetch curated samples — fixed dataset names for datasets v5."""
import json, os, sys

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
from datasets import load_dataset

cache = os.path.join(os.path.dirname(__file__), "dataset_examples")
os.makedirs(cache, exist_ok=True)

def save(name, data):
    path = os.path.join(cache, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Saved {len(data)} examples to {path}")

def try_load(dataset_id, split="train", max_n=200, cols=None):
    try:
        ds = load_dataset(dataset_id, split=split, streaming=True)
        examples = []
        for i, row in enumerate(ds):
            if i >= max_n:
                break
            if cols:
                examples.append({k: row.get(k, "") for k in cols})
            else:
                examples.append(dict(row))
        print(f"  {dataset_id}: {len(examples)} rows")
        return examples
    except Exception as e:
        print(f"  {dataset_id}: FAILED — {e}")
        return None

# Try various known-good mental-health-relevant datasets
datasets_to_try = [
    ("heliosbrahma/mental_health_chatbot_dataset", 200, ["text", "response"]),
    ("dair-ai/emotion", 200, ["text", "label"]),
    ("go_emotions", 200, ["text", "labels"]),
    ("empathetic_dialogues", 200, ["context", "utterance", "emotion", "prompt"]),
    ("nbertagnolli/counsel-chat", 200, ["questionTitle", "questionText", "answerText"]),
]

print("Downloading datasets...\n")
for ds_id, n, cols in datasets_to_try:
    data = try_load(ds_id, max_n=n, cols=cols)
    if data:
        safe_name = ds_id.split("/")[-1] if "/" in ds_id else ds_id
        save(safe_name, data)

print("\nDone.")
