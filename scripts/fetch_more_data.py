"""Download more therapy/mental health examples — using huggingface_hub directly for datasets v5 issues."""
import json, os, csv, io, random
from huggingface_hub import HfApi, hf_hub_download
from datasets import load_dataset

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
random.seed(42)

cache = os.path.join(os.path.dirname(__file__), "dataset_examples")
os.makedirs(cache, exist_ok=True)

def save(name, data):
    path = os.path.join(cache, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"  → {len(data)} saved to {name}.json")

def fetch_goemotions_direct():
    """Download go_emotions raw CSV from HF Hub directly."""
    try:
        path = hf_hub_download("google/go_emotions", "data/train.tsv", repo_type="dataset")
        examples = []
        with open(path, encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i == 0:
                    continue
                parts = line.strip().split("\t")
                if len(parts) >= 2 and parts[0].strip():
                    examples.append({"text": parts[0], "labels_raw": parts[1]})
        save("goemotions_direct", examples[:200])
    except Exception as e:
        print(f"  go_emotions direct FAILED: {e}")

def fetch_empathetic_direct():
    """Try downloading empathetic_dialogues raw CSV."""
    try:
        path = hf_hub_download("empathetic_dialogues", "empathetic_dialogues/train.csv", repo_type="dataset")
        examples = []
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= 300:
                    break
                examples.append({
                    "utterance": row.get("utterance", ""),
                    "context": row.get("context", ""),
                    "emotion": row.get("emotion", ""),
                    "prompt": row.get("prompt", ""),
                })
        save("empathetic_direct", examples)
    except Exception as e:
        print(f"  empathetic_direct FAILED: {e}")

def fetch_daic_woz():
    """Distress Analysis Interview Corpus — clinical interviews with PHQ-8 scores."""
    try:
        ds = load_dataset("AkshayChavan1/daic-woz", split="train", streaming=True)
        examples = []
        for i, row in enumerate(ds):
            if i >= 100:
                break
            examples.append(dict(row))
        save("daic_woz", examples)
    except Exception as e:
        print(f"  daic_woz FAILED: {e}")

def fetch_more_mental_health():
    """Try additional mental health datasets."""
    candidates = [
        "heliosbrahma/mental_health_chatbot_dataset",
        "AayushRBordia/counsel_chat",
    ]
    for ds_id in candidates:
        try:
            split = "train"
            ds = load_dataset(ds_id, split=split, streaming=True)
            examples = []
            for i, row in enumerate(ds):
                if i >= 300:
                    break
                examples.append(dict(row))
            safe = ds_id.split("/")[-1].replace("-", "_")
            save(safe, examples)
        except Exception as e:
            print(f"  {ds_id} FAILED: {e}")

def fetch_emotion_basic():
    """Already have this, but get more labels mapped."""
    try:
        ds = load_dataset("dair-ai/emotion", split="train", streaming=True)
        examples = []
        label_map = {0: "sadness", 1: "joy", 2: "love", 3: "anger", 4: "fear", 5: "surprise"}
        for i, row in enumerate(ds):
            if i >= 500:
                break
            examples.append({"text": row["text"], "label": row["label"], "label_name": label_map.get(row["label"], str(row["label"]))})
        save("emotion_full", examples)
    except Exception as e:
        print(f"  emotion_full FAILED: {e}")

def fetch_crisis_text():
    """Crisis-related text examples from public Reddit mental health datasets."""
    try:
        ds = load_dataset("jianqiangMa/crisis-text-classification", split="train", streaming=True)
        examples = []
        for i, row in enumerate(ds):
            if i >= 200:
                break
            examples.append(dict(row))
        save("crisis_text", examples)
    except Exception as e:
        print(f"  crisis_text FAILED: {e}")

if __name__ == "__main__":
    print("Fetching datasets...\n")
    fetch_goemotions_direct()
    fetch_empathetic_direct()
    fetch_daic_woz()
    fetch_more_mental_health()
    fetch_emotion_basic()
    fetch_crisis_text()
    print("\nDone.")
