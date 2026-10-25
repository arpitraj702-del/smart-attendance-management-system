"""Real face recognition with OpenCV: YuNet (detection) + SFace (128-D embeddings).

Recognition = comparing a live face's embedding against stored embeddings with
cosine similarity. Faces that do not clear the threshold are "Unknown".
"""
import base64
import threading
from dataclasses import dataclass

import cv2
import numpy as np

from config import Config

EMBEDDING_DIM = 128


class ModelsMissingError(RuntimeError):
    pass


@dataclass
class DetectedFace:
    box: tuple          # x, y, w, h (pixels in the analysed image)
    score: float        # detector confidence
    embedding: np.ndarray  # L2-normalised float32[128]


def decode_image(data):
    """data-URL / base64 string or raw bytes -> BGR image (max side 1280 px)."""
    if isinstance(data, str):
        if data.startswith("data:") and "," in data:
            data = data.split(",", 1)[1]
        data = base64.b64decode(data, validate=False)
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image")
    longest = max(img.shape[:2])
    if longest > 1280:
        scale = 1280 / longest
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return img


class FaceEngine:
    def __init__(self):
        missing = [p.name for p in (Config.DETECTOR_MODEL, Config.RECOGNIZER_MODEL) if not p.exists()]
        if missing:
            raise ModelsMissingError(
                "Face models not found (" + ", ".join(missing) + "). Run:  python download_models.py"
            )
        self._detector = cv2.FaceDetectorYN.create(str(Config.DETECTOR_MODEL), "", (320, 320), 0.85, 0.3, 5000)
        self._recognizer = cv2.FaceRecognizerSF.create(str(Config.RECOGNIZER_MODEL), "")
        self._lock = threading.Lock()  # OpenCV DNN objects are not thread-safe

    def analyse(self, img):
        """Detect every face in `img` and compute its embedding."""
        h, w = img.shape[:2]
        found = []
        with self._lock:
            self._detector.setInputSize((w, h))
            _, faces = self._detector.detect(img)
            if faces is None:
                return found
            for row in faces:
                aligned = self._recognizer.alignCrop(img, row)
                feat = self._recognizer.feature(aligned).flatten().astype(np.float32)
                norm = float(np.linalg.norm(feat))
                if feat.size != EMBEDDING_DIM or norm == 0:
                    continue
                x, y, bw, bh = [int(round(float(v))) for v in row[:4]]
                x, y = max(x, 0), max(y, 0)
                bw, bh = min(bw, w - x), min(bh, h - y)
                found.append(DetectedFace((x, y, bw, bh), float(row[14]), feat / norm))
        return found


class FaceIndex:
    """All stored embeddings in memory for fast matching."""

    def __init__(self):
        self._lock = threading.RLock()
        self.ids = np.empty(0, dtype=np.int64)
        self.matrix = np.empty((0, EMBEDDING_DIM), dtype=np.float32)
        self.loaded = False

    def load(self, rows):
        ids, vecs = [], []
        for r in rows:
            v = np.frombuffer(bytes(r["embedding"]), dtype=np.float32)
            if v.size != EMBEDDING_DIM:
                continue
            n = np.linalg.norm(v)
            if n == 0:
                continue
            ids.append(int(r["student_id"]))
            vecs.append(v / n)
        with self._lock:
            self.ids = np.array(ids, dtype=np.int64)
            self.matrix = np.vstack(vecs).astype(np.float32) if vecs else np.empty((0, EMBEDDING_DIM), np.float32)
            self.loaded = True

    def best(self, emb):
        """(student_id, similarity) of the closest stored face, or (None, -1)."""
        with self._lock:
            if self.ids.size == 0:
                return None, -1.0
            sims = self.matrix @ emb
            i = int(np.argmax(sims))
            return int(self.ids[i]), float(sims[i])

    def match(self, emb):
        """Return (student_id or None, best_similarity). None => Unknown User."""
        with self._lock:
            if self.ids.size == 0:
                return None, -1.0
            sims = self.matrix @ emb
            i = int(np.argmax(sims))
            best, sid = float(sims[i]), int(self.ids[i])
            others = sims[self.ids != sid]
            second = float(others.max()) if others.size else -1.0
        if best < Config.MATCH_THRESHOLD:
            return None, best
        if second >= Config.MATCH_THRESHOLD and best - second < Config.MATCH_MARGIN:
            return None, best  # ambiguous between two students -> never guess
        return sid, best


def crop_thumbnail(img, box, size=240):
    """Square JPEG thumbnail around a face (bytes)."""
    h, w = img.shape[:2]
    x, y, bw, bh = box
    side = int(max(bw, bh) * 1.6)
    cx, cy = x + bw // 2, y + bh // 2
    x0, y0 = max(cx - side // 2, 0), max(cy - side // 2, 0)
    x1, y1 = min(x0 + side, w), min(y0 + side, h)
    crop = img[y0:y1, x0:x1]
    crop = cv2.resize(crop, (size, size), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return buf.tobytes() if ok else b""
