"""Central configuration. Values come from the .env file (see .env.example)."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    MAX_CONTENT_LENGTH = 40 * 1024 * 1024  # registration sends several photos

    # --- Security & Session --------------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("FLASK_ENV") == "production"
    PERMANENT_SESSION_LIFETIME = 28800  # 8 hours

    # --- MySQL ---------------------------------------------------------
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "smart_attendance")
    DB_SSL_CA = os.getenv("DB_SSL_CA", "")

    # --- Initial Bootstrap (used only on first database initialization) -
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

    # --- Face recognition ---------------------------------------------
    MODELS_DIR = BASE_DIR / "models"
    DETECTOR_MODEL = MODELS_DIR / "face_detection_yunet_2023mar.onnx"
    RECOGNIZER_MODEL = MODELS_DIR / "face_recognition_sface_2021dec.onnx"
    PHOTO_DIR = BASE_DIR / "uploads" / "faces"
    MATCH_THRESHOLD = float(os.getenv("MATCH_THRESHOLD", "0.40"))
    MATCH_MARGIN = float(os.getenv("MATCH_MARGIN", "0.05"))
    CONFIRM_FRAMES = int(os.getenv("CONFIRM_FRAMES", "2"))
    MIN_FACE_PX = 80          # smallest face accepted at registration
    MIN_RECOGNIZE_PX = 60     # smaller faces in live view are never matched
    MAX_PHOTOS = 10

    # --- Attendance rules (must match schema.sql views) ----------------
    GOOD_PCT = 80.0       # >= 80  -> Good
    WARNING_PCT = 75.0    # 75-79.99 -> Warning, < 75 -> Critical / debarred

    @classmethod
    def check_production_guard(cls):
        """Warns or aborts if default/insecure keys are used in production."""
        is_prod = os.getenv("FLASK_ENV") == "production"
        insecure_keys = ("dev-only-change-me", "replace-this-with-a-long-random-string", "")
        if cls.SECRET_KEY in insecure_keys:
            msg = "[SECURITY WARNING] Application is using an insecure default SECRET_KEY in .env!"
            if is_prod:
                raise RuntimeError(msg + " Set a unique SECRET_KEY before running in production.")
            print(msg, file=sys.stderr)
