
import random
import time

from pathlib import Path
from collections import Counter

from backend.recognition.classifier import recognize


DATASET = Path("datasets/trashnet/dataset-resized")

CATEGORIES = [
    "plastic",
    "glass",
    "metal",
    "paper",
    "cardboard",
    "trash"
]

SAMPLES = 10

random.seed(42)

total = 0
correct = 0
uncertain = 0
accepted = 0
accepted_correct = 0

confusion = Counter()

start = time.perf_counter()

for category in CATEGORIES:

    images = sorted((DATASET / category).glob("*.jpg"))

    selected = random.sample(
        images, min(SAMPLES, len(images))
    )

    category_correct = 0

    print(f"\nTesting {category.upper()}")

    for image in selected:

        result = recognize(image)

        predicted = result["material"]
        score = result["confidence"]
        needs_help = result["needs_clarification"]

        total += 1

        is_correct = predicted == category

        if is_correct:
            correct += 1
            category_correct += 1

        if needs_help:
            uncertain += 1
        else:
            accepted += 1

            if is_correct:
                accepted_correct += 1

        confusion[(category, predicted)] += 1

        status = "CORRECT" if is_correct else "WRONG"

        print(
            f"{image.name:18} "
            f"{predicted:12} "
            f"{score:.2%} "
            f"{status} "
            f"clarify={needs_help}"
        )

    if selected:
        print(
            f"Category accuracy: "
            f"{category_correct}/{len(selected)}"
        )

print("\n" + "=" * 45)
print("FINAL EVALUATION")
print("=" * 45)

print(f"Total images: {total}")
print(f"Correct predictions: {correct}")

if total:
    print(f"Raw accuracy: {correct / total:.2%}")
    print(f"Clarification rate: {uncertain / total:.2%}")
    print(f"Accepted rate: {accepted / total:.2%}")

if accepted:
    print(
        f"Accepted accuracy: "
        f"{accepted_correct / accepted:.2%}"
    )

print(f"Total runtime: {time.perf_counter() - start:.2f}s")

print("\nPrediction distribution:")

for (actual, predicted), count in sorted(confusion.items()):
    print(f"{actual} -> {predicted}: {count}")
