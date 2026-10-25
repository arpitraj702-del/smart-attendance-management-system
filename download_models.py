"""Download the two OpenCV Zoo ONNX models used for face detection (YuNet) and recognition (SFace)."""
import sys
import urllib.request
from pathlib import Path

MODELS = {
    "face_detection_yunet_2023mar.onnx": (
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        100_000,       # expected ~230 KB
    ),
    "face_recognition_sface_2021dec.onnx": (
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
        10_000_000,    # expected ~37 MB
    ),
}
DEST = Path(__file__).resolve().parent / "models"


def main():
    DEST.mkdir(exist_ok=True)
    failed = False
    for name, (url, min_size) in MODELS.items():
        target = DEST / name
        if target.exists() and target.stat().st_size >= min_size:
            print(f"[ok]   {name} already present")
            continue
        print(f"[get]  {name}")
        try:
            urllib.request.urlretrieve(url, target)
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {name}: {exc}")
            failed = True
            continue
        if target.stat().st_size < min_size:
            print(f"[FAIL] {name}: file is only {target.stat().st_size} bytes (expected >= {min_size}).")
            target.unlink(missing_ok=True)
            failed = True
        else:
            print(f"[ok]   saved {target.stat().st_size / 1e6:.1f} MB")
    if failed:
        print("\nAutomatic download failed. Download the two .onnx files manually from")
        print("  https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet")
        print("  https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface")
        print(f"and put them in: {DEST}")
        sys.exit(1)
    print("\nAll models ready.")


if __name__ == "__main__":
    main()
