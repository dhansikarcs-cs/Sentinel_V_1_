import json

with open("scripts/sentinel_finetune.ipynb") as f:
    nb = json.load(f)

# Cell 4 = training data (inline). Replace with file upload version.
nb["cells"][4] = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {"id": "load_data"},
    "source": [
        "# 4. Upload training data (500 examples)\n",
        "from google.colab import files\n",
        "from datasets import Dataset\n",
        "from unsloth.chat_templates import get_chat_template, standardize_sharegpt\n",
        "import json\n",
        "\n",
        "tokenizer = get_chat_template(tokenizer, chat_template='mistral')\n",
        "\n",
        "print('Please upload sentinel_training_500.json')\n",
        "uploaded = files.upload()\n",
        "filename = list(uploaded.keys())[0]\n",
        "training_data = json.loads(uploaded[filename])\n",
        "print(f'Loaded {len(training_data)} examples')\n",
        "\n",
        "dataset = Dataset.from_list(training_data)\n",
        "dataset = standardize_sharegpt(dataset)\n",
        "\n",
        "def format_chat(examples):\n",
        "    outputs = tokenizer.apply_chat_template(\n",
        "        examples['conversations'], tokenize=False\n",
        "    )\n",
        "    return {'text': outputs}\n",
        "\n",
        "dataset = dataset.map(format_chat, batched=True)\n",
        "print('Sample:\\n', dataset[0]['text'][:300])\n",
    ],
}

# Update cell 5 title
for i, line in enumerate(nb["cells"][5]["source"]):
    if "# 5. Train!" in line:
        nb["cells"][5]["source"][i] = "# 5. Train! (~20-25 min for 500 examples)\n"

with open("scripts/sentinel_finetune.ipynb", "w") as f:
    json.dump(nb, f, indent=2)

print("Notebook updated. Cell 4 now loads uploaded JSON.")
print(f"Total cells: {len(nb['cells'])}")
