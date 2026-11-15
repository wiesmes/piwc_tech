from io import BytesIO
from threading import Lock

from PIL import Image, ImageOps


class RealProvider:

    def __init__(self, mode="multi"):
        if mode not in {"single", "multi"}:
            raise ValueError("Invalid recognition mode")

        self.mode = mode
        self.lock = Lock()

        if mode == "single":
            from .classifier import recognize
            self.recognizer = recognize

        else:
            from .multi_classifier import recognize_multiple
            self.recognizer = recognize_multiple

    def recognize(self, image_bytes, hint=None):

        # Convert uploaded bytes into a PIL image.
        with Image.open(BytesIO(image_bytes)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")

        # Prevent overlapping inference requests.
        with self.lock:
            result = self.recognizer(image)

        return result