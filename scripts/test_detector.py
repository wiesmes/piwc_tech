
import json
import sys

from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

from backend.recognition.detector import detect_objects


image = ImageOps.exif_transpose(
    Image.open(sys.argv[1])
).convert("RGB")

result = detect_objects(image)

print(json.dumps(result, indent=4))

draw = ImageDraw.Draw(image)

for i, detection in enumerate(
    result["detections"], start=1
):

    box = detection["bbox"]

    label = (
        f'{i}: {detection["detected_item"]} '
        f'{detection["detection_score"]:.0%}'
    )

    draw.rectangle(
        box,
        outline="lime",
        width=5
    )

    text_position = (
        box[0],
        max(0, box[1] - 15)
    )

    text_box = draw.textbbox(text_position, label)

    draw.rectangle(text_box, fill="black")
    draw.text(text_position, label, fill="white")

Path("outputs").mkdir(exist_ok=True)

image.save("outputs/detected_objects.jpg")

print("\nSaved: outputs/detected_objects.jpg")
