"""Check the face engine on your own photos:

    python face_check.py photo_a.jpg photo_b.jpg

Prints the cosine similarity between the (single) face in each photo and whether it
would count as the same person under the current MATCH_THRESHOLD.
"""
import sys

import cv2
import numpy as np

from config import Config
from face_engine import FaceEngine, ModelsMissingError


def load(engine, path):
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        sys.exit(f"Cannot read image: {path}")
    faces = engine.analyse(img)
    if len(faces) != 1:
        sys.exit(f"{path}: expected exactly 1 face, found {len(faces)}")
    return faces[0]


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    try:
        engine = FaceEngine()
    except ModelsMissingError as exc:
        sys.exit(str(exc))
    a, b = load(engine, sys.argv[1]), load(engine, sys.argv[2])
    sim = float(a.embedding @ b.embedding)
    verdict = "SAME person" if sim >= Config.MATCH_THRESHOLD else "DIFFERENT people"
    print(f"cosine similarity = {sim:.3f}  (threshold {Config.MATCH_THRESHOLD})  ->  {verdict}")


if __name__ == "__main__":
    main()
