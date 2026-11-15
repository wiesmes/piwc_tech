
import sys
import time
import torch

from PIL import Image
from transformers import CLIPModel, CLIPProcessor

# Select GPU if available.
device = "mps" if torch.backends.mps.is_available() else "cpu"

print("Using device:", device)
print("Loading CLIP model...")

model_path = "models/clip-vit-base-patch32"

model = CLIPModel.from_pretrained(model_path).to(device)
processor = CLIPProcessor.from_pretrained(model_path)

model.eval()

# Define possible waste categories and descriptive labels
labels = [
    "plastic water bottle",
    "plastic food container",
    "plastic bag",
    "aluminum beverage can",
    "metal food can",
    "glass bottle",
    "glass jar",
    "cardboard box",
    "office paper",
    "newspaper",
    "banana peel",
    "apple core",
    "leftover food scraps",
    "plastic snack wrapper",
    "disposable coffee cup",
    "styrofoam container",
    "plastic fork or spoon",
    "paper napkin",
    "greasy pizza box",
    "unrecognized object",
    "empty background"
]

prompts = [
    f"a photo of {label}" for label in labels
]

# Load the image provided in the terminal.
image = Image.open(sys.argv[1]).convert("RGB")

inputs = processor(
    text=prompts,
    images=image,
    return_tensors="pt",
    padding=True
).to(device)

start = time.perf_counter()

with torch.inference_mode():
    outputs = model(**inputs)
    scores = outputs.logits_per_image.softmax(dim=1)[0]

scores = scores.cpu()

elapsed = time.perf_counter() - start

print("\nRecognition results:")
print("-" * 35)

# Display predictions from highest to lowest.
for i in torch.argsort(scores, descending=True):
    index = i.item()
    print(f"{labels[index]:20} {scores[index].item():.2%}")

best = scores.argmax().item()

print("\nPredicted item:", labels[best])
print(f"Model score: {scores[best].item():.2%}")
print(f"Inference time: {elapsed:.3f} seconds")
