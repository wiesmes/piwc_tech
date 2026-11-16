import cv2
import time
import json
import argparse

from PIL import Image
from pathlib import Path


def get_recognizer(mode):
    if mode == "multi":
        from .multi_classifier import recognize_multiple
        return recognize_multiple

    from .classifier import recognize
    return recognize


def run_camera(mode="single", camera_index=0, continuous=False):

    recognize = get_recognizer(mode)

    camera = cv2.VideoCapture(camera_index)

    if not camera.isOpened():
        camera.release()
        raise RuntimeError("Unable to open camera.")

    output_folder = Path("outputs")
    output_folder.mkdir(exist_ok=True)

    capture_count = 0

    try:
        time.sleep(1)

        print(f"Recognition mode: {mode}")
        print("Press SPACE to capture.")
        print("Press Q to quit.")

        while True:
            success, frame = camera.read()

            if not success:
                raise RuntimeError("Unable to capture frame.")

            cv2.imshow("Smart Waste Sorter", frame)

            key = cv2.waitKey(1) & 0xFF

            if key in (ord("q"), ord("Q"), 27):
                break

            if key == ord(" "):
                capture_count += 1

                rgb = cv2.cvtColor(
                    frame, cv2.COLOR_BGR2RGB
                )

                image = Image.fromarray(rgb)

                image_path = (
                    output_folder / "camera_capture.jpg"
                )

                image.save(image_path, quality=95)

                print("\n" + "=" * 50)
                print("Capture:", capture_count)
                print("Processing image...")

                start = time.perf_counter()

                result = recognize(str(image_path))

                print(json.dumps(result, indent=4))

                print(
                    "Recognition time:",
                    round(time.perf_counter() - start, 3),
                    "seconds"
                )

                if not continuous:
                    return result

                print("\nReady for next item.")
                print("Press SPACE to capture or Q to quit.")
   
    except KeyboardInterrupt:
        print("\nCamera session stopped.")

    finally:
        camera.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--mode",
        choices=["single", "multi"],
        default="single"
    )

    parser.add_argument(
        "--camera",
        type=int,
        default=0
    )

    parser.add_argument(
        "--continuous",
        action="store_true"
    )

    args = parser.parse_args()

    run_camera(
        mode=args.mode,
        camera_index=args.camera,
        continuous=args.continuous
    )
