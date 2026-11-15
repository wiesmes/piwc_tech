
import random
import torch
import time

from pathlib import Path
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

device = "mps" if torch.backends.mps.is_available() else "cpu"

model_path = "models/clip-vit-base-patch32"

model = CLIPModel.from_pretrained(model_path).to(device)
processor = CLIPProcessor.from_pretrained(model_path)

model.eval()

categories = {
    "plastic": [
        "plastic packaging",
        "discarded plastic material",
        "a plastic bottle or container"
    ],
    "glass": [
        "glass waste",
        "a glass bottle or jar",
        "discarded glass material"
    ],
    "metal": [
        "metal waste",
        "an aluminum or steel can",
        "discarded metallic material"
    ],
    "paper": [
        "discarded paper",
        "a sheet of paper or newspaper",
        "paper waste"
    ],
    "cardboard": [
        "corrugated cardboard",
        "a discarded cardboard box",
        "brown cardboard packaging"
    ],
    "organic": [
        "food waste",
        "fruit and vegetable scraps",
        "discarded organic food"
    ],
    "unknown": [
        "mixed miscellaneous garbage",
        "an unidentified object",
        "an empty surface"
    ]
}

labels = list(categories.keys())

prompts = [
    f"a photo of {description}"
    for descriptions in categories.values()
    for description in descriptions
]

dataset = Path("datasets/trashnet/dataset-resized")

random.seed(42)

total = 0
correct = 0

start = time.perf_counter()

for category in [
    "plastic", "glass", "metal", "paper", "cardboard"
]:

    images = sorted((dataset / category).glob("*.jpg"))

    selected = random.sample(images, min(10, len(images)))

    category_correct = 0

    print(f"\nTesting {category.upper()}")

    for path in selected:

        image = Image.open(path).convert("RGB")

        inputs = processor(
            text=prompts,
            images=image,
            return_tensors="pt",
            padding=True
        ).to(device)

        with torch.inference_mode():
            outputs = model(**inputs)

            logits = outputs.logits_per_image[0]

            # Average the three prompts per material.
            grouped = logits.reshape(len(labels), 3).mean(dim=1)

            scores = grouped.softmax(dim=0).cpu()

        prediction = labels[scores.argmax().item()]

        total += 1

        if prediction == category:
            correct += 1
            category_correct += 1

        print(f"{path.name}: {prediction}")

    print(f"Correct: {category_correct}/{len(selected)}")

print("\nFINAL RESULTS")
print(f"Total images: {total}")
print(f"Correct: {correct}")

if total:
    print(f"Accuracy: {correct / total:.2%}")

print(f"Runtime: {time.perf_counter() - start:.2f}s")
