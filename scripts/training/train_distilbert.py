import sys, csv, math, os
from pathlib import Path

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification, AdamW, get_linear_schedule_with_warmup

SRC = Path(__file__).resolve().parents[2] / "software" / "data" / "rnd" / "goemotions_clean.csv"
OUT = Path(__file__).resolve().parents[2] / "software" / "models" / "emotion_distilbert"
os.makedirs(OUT, exist_ok=True)

EMOTIONS = [
    "admiration","amusement","anger","annoyance","approval","caring","confusion",
    "curiosity","desire","disappointment","disapproval","disgust","embarrassment",
    "excitement","fear","gratitude","grief","joy","love","nervousness","optimism",
    "pride","realization","relief","remorse","sadness","surprise","neutral",
]
NUM_LABELS = len(EMOTIONS)

BATCH_SIZE = 32
EPOCHS = 2
MAX_LEN = 64
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class GoEmotionsDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_len):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
        inputs = self.tokenizer(
            text, max_length=self.max_len, padding="max_length", truncation=True, return_tensors="pt"
        )
        return {
            "input_ids": inputs["input_ids"].squeeze(0),
            "attention_mask": inputs["attention_mask"].squeeze(0),
            "labels": torch.tensor(self.labels[idx], dtype=torch.float),
        }


def load_data(path):
    texts, labels = [], []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = row["text"].strip()
            if not text or len(text) < 2:
                continue
            label = [int(row[em]) for em in EMOTIONS]
            texts.append(text)
            labels.append(label)
    return texts, labels


def main():
    print(f"Device: {DEVICE}")

    texts, labels = load_data(SRC)
    print(f"Loaded {len(texts)} examples with {NUM_LABELS} emotion labels")

    tokenizer = DistilBertTokenizer.from_pretrained("distilbert-base-uncased")
    dataset = GoEmotionsDataset(texts, labels, tokenizer, MAX_LEN)

    split = int(len(dataset) * 0.9)
    train_ds, eval_ds = torch.utils.data.Subset(dataset, range(split)), torch.utils.data.Subset(dataset, range(split, len(dataset)))
    print(f"Train: {len(train_ds)}, Eval: {len(eval_ds)}")

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    eval_loader = DataLoader(eval_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    model = DistilBertForSequenceClassification.from_pretrained("distilbert-base-uncased", num_labels=NUM_LABELS, problem_type="multi_label_classification")
    model.to(DEVICE)

    optimizer = AdamW(model.parameters(), lr=2e-5, correct_bias=False)
    total_steps = len(train_loader) * EPOCHS
    scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=int(0.1 * total_steps), num_training_steps=total_steps)

    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0
        for batch in train_loader:
            input_ids = batch["input_ids"].to(DEVICE)
            attention_mask = batch["attention_mask"].to(DEVICE)
            labels = batch["labels"].to(DEVICE)
            optimizer.zero_grad()
            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            total_loss += loss.item()

        avg_loss = total_loss / len(train_loader)
        model.eval()
        correct, total = 0, 0
        with torch.no_grad():
            for batch in eval_loader:
                input_ids = batch["input_ids"].to(DEVICE)
                attention_mask = batch["attention_mask"].to(DEVICE)
                labels = batch["labels"].to(DEVICE)
                outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                preds = (torch.sigmoid(outputs.logits) > 0.5).int()
                correct += (preds == labels.int()).sum().item()
                total += labels.numel()
        acc = correct / total * 100
        print(f"Epoch {epoch+1}/{EPOCHS} | Loss: {avg_loss:.4f} | Token-level accuracy: {acc:.2f}%")

    model.save_pretrained(OUT)
    tokenizer.save_pretrained(OUT)
    print(f"Model saved to {OUT}")

    model.eval()
    tests = [
        "That game hurt.",
        "I'm so excited! I got the job!",
        "My cat died today. I don't know what to do with myself.",
        "Feeling okay today. Nothing special.",
    ]
    for t in tests:
        inputs = tokenizer(t, return_tensors="pt", max_length=MAX_LEN, truncation=True, padding=True).to(DEVICE)
        with torch.no_grad():
            logits = model(**inputs).logits
        probs = torch.sigmoid(logits).cpu().numpy()[0]
        predicted = [EMOTIONS[i] for i, p in enumerate(probs) if p > 0.5]
        print(f"  \"{t}\" -> {predicted if predicted else ['neutral']}")


if __name__ == "__main__":
    main()
