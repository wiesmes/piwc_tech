import json
import sys
import time

from pathlib import Path
from PIL import Image, ImageOps
from .detector import detect_objects
from .classifier import recognize
from .fusion import fuse_predictions


def recognize_multiple(image):
    start = time.perf_counter()

    if not isinstance(image, Image.Image):
        image = Image.open(image)

    image = ImageOps.exif_transpose(image).convert("RGB")

    # Detect individual objects using OWLv2.
    detection_result = detect_objects(image)

    objects = []

    crop_folder = Path("outputs/crops")
    crop_folder.mkdir(parents=True, exist_ok=True)

    for i, detection in enumerate(
        detection_result["detections"], start=1
    ):
        # Crop the detected object.
        x1, y1, x2, y2 = detection["bbox"]
        cropped_image = image.crop((x1, y1, x2, y2))

        cropped_image.save(
            crop_folder / f"object_{i}.jpg"
        )

        # Classify each object using CLIP.
        classification = recognize(cropped_image)

        result = fuse_predictions(
            detection,
            classification
        )

        objects.append({
            **result,
            "object_id": i,
            "detector_label": detection["detected_item"],
            "detection_score": detection["detection_score"],
            "bbox": detection["bbox"]
        })

    return {
        "object_count": len(objects),
        "multiple_items": len(objects) > 1,
        "objects": objects,
        "needs_clarification": (
            len(objects) == 0
            or any(
                obj["needs_clarification"]
                for obj in objects
            )
        ),
        "detection_time_seconds": detection_result[
            "detection_time_seconds"
        ],
        "total_time_seconds": round(
            time.perf_counter() - start, 3
        )
    }


if __name__ == "__main__":
    result = recognize_multiple(sys.argv[1])
    print(json.dumps(result, indent=4))
