
import json
import sys
import time
import torch

from pathlib import Path
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from .labels import (
    LABELS,
    AMBIGUOUS_ITEMS,
    CLARIFICATION_METADATA,
    MATERIAL_PROMPTS
)

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "models" / "clip-vit-base-patch32"

DEVICE = (
    "mps" if torch.backends.mps.is_available()
    else "cpu"
)

# Initial experimental thresholds.
MATERIAL_THRESHOLD = 0.55
OBJECT_THRESHOLD = 0.50
MARGIN_THRESHOLD = 0.10
ORGANIC_MATERIAL_THRESHOLD = 0.75
ORGANIC_OBJECT_THRESHOLD = 0.60

model = None
processor = None

material_labels = list(MATERIAL_PROMPTS.keys())
object_labels = list(LABELS.keys())

material_prompts = [
    f"a photo of {description}"
    for descriptions in MATERIAL_PROMPTS.values()
    for description in descriptions
]

object_prompts = [
    f"a photo of {label}"
    for label in object_labels
]

all_prompts = material_prompts + object_prompts


def load_model():
    global model, processor

    if model is None:
        print(f"Loading CLIP on {DEVICE}...",
              file=sys.stderr)

        processor = CLIPProcessor.from_pretrained(
            str(MODEL_PATH)
        )

        model = CLIPModel.from_pretrained(
            str(MODEL_PATH)
        ).to(DEVICE)

        model.eval()


def recognize(image):
    load_model()

    start = time.perf_counter()

    if not isinstance(image, Image.Image):
        image = Image.open(image)

    image = image.convert("RGB")

    inputs = processor(
        text=all_prompts,
        images=image,
        return_tensors="pt",
        padding=True
    ).to(DEVICE)

    # Run both classifiers in one forward pass.
    with torch.inference_mode():
        outputs = model(**inputs)
        logits = outputs.logits_per_image[0].cpu()

    split = len(material_prompts)

    # Material classification.
    material_logits = logits[:split]

    grouped = material_logits.reshape(
        len(material_labels), 3
    ).mean(dim=1)

    material_scores = grouped.softmax(dim=0)

    mat_values, mat_indices = torch.topk(
        material_scores, 2
    )

    material = material_labels[mat_indices[0].item()]
    material_confidence = mat_values[0].item()

    material_margin = (
        mat_values[0] - mat_values[1]
    ).item()

    # Specific object classification.
    object_scores = logits[split:].softmax(dim=0)

    obj_values, obj_indices = torch.topk(
        object_scores, 2
    )

    item = object_labels[obj_indices[0].item()]
    object_confidence = obj_values[0].item()

    object_margin = (
        obj_values[0] - obj_values[1]
    ).item()

    object_material = LABELS[item]

    # Find objects compatible with the predicted material.
    compatible_indices = [
        i for i, label in enumerate(object_labels)
        if LABELS[label] == material
    ]

    suggested_item = item
    suggested_score = object_confidence

    if compatible_indices and material != "unknown":

        best_index = max(
            compatible_indices,
            key=lambda i: object_scores[i].item()
        )

        suggested_item = object_labels[best_index]
        suggested_score = object_scores[best_index].item()

    # Check agreement between classifiers.
    agreement = material == object_material

    uncertain = (
        material_confidence < MATERIAL_THRESHOLD
        or object_confidence < OBJECT_THRESHOLD
        or material_margin < MARGIN_THRESHOLD
        or object_margin < MARGIN_THRESHOLD
        or not agreement
        or material == "unknown"
        or object_material == "unknown"
    )

    # Combine scores for recognized food waste objects.
    organic_score = sum(
        object_scores[i].item()
        for i, label in enumerate(object_labels)
        if LABELS[label] == "organic"
    )

    organic_verified = (
        material == "organic"
        and object_material == "organic"
        and material_confidence >= ORGANIC_MATERIAL_THRESHOLD
        and organic_score >= ORGANIC_OBJECT_THRESHOLD
        and material_margin >= MARGIN_THRESHOLD
    )

    # Accept the broader food waste category when supported.
    if organic_verified:
        item = "leftover food scraps"
        uncertain = False

    question = None
    clarification_type = None
    required_attributes = []

    if uncertain:
        question = "Please reposition or identify the item."

        if (
            material == "unknown"
            or not agreement
            or material_confidence < MATERIAL_THRESHOLD
            or material_margin < MARGIN_THRESHOLD
            or object_material == "unknown"
        ):
            clarification_type = "material"

        else:
            clarification_type = "identity"

    elif item in AMBIGUOUS_ITEMS:
        question = AMBIGUOUS_ITEMS[item]

        metadata = CLARIFICATION_METADATA.get(item, {})

        clarification_type = metadata.get(
            "clarification_type", "identity"
        )

        required_attributes = list(
            metadata.get("required_attributes", [])
        )

    needs_clarification = (
        uncertain or item in AMBIGUOUS_ITEMS
    )

    return {
        "item": item,
        "material": material,
        "suggested_item": suggested_item,
        "suggested_item_score": round(suggested_score, 4),
        "confidence": round(object_confidence, 4),
        "material_confidence": round(
            material_confidence, 4
        ),
        "organic_group_score": round(organic_score, 4),
        "organic_verified": organic_verified,
        "object_material": object_material,
        "prediction_agreement": agreement,
        "needs_clarification": needs_clarification,
        "clarification_type": clarification_type,
        "required_attributes": required_attributes,
        "question": question,
        "inference_time_seconds": round(
            time.perf_counter() - start, 3
        )
    }


if __name__ == "__main__":
    result = recognize(sys.argv[1])
    print(json.dumps(result, indent=4))
