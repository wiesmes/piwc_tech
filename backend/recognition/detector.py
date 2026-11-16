
import torch
import time

from pathlib import Path
from PIL import Image, ImageOps
from torchvision.ops import nms
from transformers import (
    Owlv2Processor,
    Owlv2ForObjectDetection
)

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "models" / "owlv2"

DEVICE = (
    "mps" if torch.backends.mps.is_available()
    else "cpu"
)

DETECTION_THRESHOLD = 0.30
NMS_THRESHOLD = 0.35
CONTAINMENT_THRESHOLD = 0.70
MAX_OBJECTS = 10


DETECTION_LABELS = [
    "plastic water bottle",
    "plastic beverage bottle",
    "plastic food container",
    "plastic bag",
    "aluminum beverage can",
    "metal food can",
    "glass bottle",
    "glass jar",
    "cardboard box",
    "sheet of paper",
    "newspaper",
    "paper napkin",
    "paper towel",
    "banana peel",
    "apple core",
    "food scraps",
    "leftover salad",
    "plastic snack wrapper",
    "biscuit wrapper",
    "candy wrapper",
    "disposable coffee cup",
    "styrofoam container",
    "plastic utensils",
    "pizza box",
    "rubber band",
    "rubber object",
    "rubber glove"
]

model = None
processor = None


def load_detector():
    global model, processor

    if model is None:
        print(f"Loading OWLv2 on {DEVICE}...")

        processor = Owlv2Processor.from_pretrained(
            str(MODEL_PATH)
        )

        model = Owlv2ForObjectDetection.from_pretrained(
            str(MODEL_PATH)
        ).to(DEVICE)

        model.eval()

def containment(box1, box2):
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    intersection = (
        max(0, x2 - x1) *
        max(0, y2 - y1)
    )

    area1 = (
        (box1[2] - box1[0]) *
        (box1[3] - box1[1])
    )

    area2 = (
        (box2[2] - box2[0]) *
        (box2[3] - box2[1])
    )

    smaller_area = min(area1, area2)

    if smaller_area <= 0:
        return 0

    return intersection / smaller_area


def detect_objects(image):
    load_detector()

    start = time.perf_counter()

    if not isinstance(image, Image.Image):
        image = Image.open(image)

    image = ImageOps.exif_transpose(image).convert("RGB")

    prompts = [
        f"a photo of {label}"
        for label in DETECTION_LABELS
    ]

    detection_image = image.copy()
    detection_image.thumbnail((1024, 1024))

    inputs = processor(
        text=[prompts],
        images=detection_image,
        return_tensors="pt"
    ).to(DEVICE)

    with torch.inference_mode():
        outputs = model(**inputs)

    target_sizes = torch.tensor(
        [[image.height, image.width]],
        device=outputs.pred_boxes.device
    )

    if hasattr(
        processor,
        "post_process_grounded_object_detection"
    ):
        results = processor.post_process_grounded_object_detection(
            outputs=outputs,
            target_sizes=target_sizes,
            threshold=DETECTION_THRESHOLD
        )[0]

    else:
        results = processor.post_process_object_detection(
            outputs=outputs,
            target_sizes=target_sizes,
            threshold=DETECTION_THRESHOLD
        )[0]

    boxes = results["boxes"].cpu()
    scores = results["scores"].cpu()
    labels = results["labels"].cpu()

    # Remove duplicate overlapping detections.
    keep = nms(boxes, scores, NMS_THRESHOLD)

    filtered = []

    # Remove highly contained boxes with the same label.
    for index in keep:
        i = index.item()

        duplicate = any(
        containment(
            boxes[i].tolist(),
            boxes[j].tolist()
        ) >= CONTAINMENT_THRESHOLD
        for j in filtered
    )

        if not duplicate:
            filtered.append(i)

    detections = []

    for i in filtered[:MAX_OBJECTS]:

        x1, y1, x2, y2 = boxes[i].tolist()

        x1 = max(0, int(x1))
        y1 = max(0, int(y1))
        x2 = min(image.width, int(x2 + 1))
        y2 = min(image.height, int(y2 + 1))

        if x2 <= x1 or y2 <= y1:
            continue

        detections.append({
            "detected_item": DETECTION_LABELS[
                labels[i].item()
            ],
            "detection_score": round(
                scores[i].item(), 4
            ),
            "bbox": [x1, y1, x2, y2]
        })

    return {
        "object_count": len(detections),
        "detections": detections,
        "detection_time_seconds": round(
            time.perf_counter() - start, 3
        )
    }
