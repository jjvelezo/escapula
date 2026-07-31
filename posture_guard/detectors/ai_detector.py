"""AI-mode detector: MediaPipe Tasks PoseLandmarker (33-point BlazePose).

Runs fully on-device (MediaPipe's bundled CPU/XNNPACK runtime) — no network
calls happen here except the one-time model download on first run.
"""
from __future__ import annotations

import time
import urllib.request
from pathlib import Path
from typing import Optional

import numpy as np
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions
import mediapipe as mp

from .. import angles as ang
from .base import PostureReading

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
)
MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"
MODEL_PATH = MODELS_DIR / "pose_landmarker_lite.task"


def ensure_model_downloaded() -> Path:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    if not MODEL_PATH.exists():
        print(f"Downloading pose model to {MODEL_PATH} (one-time)...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Model downloaded.")
    return MODEL_PATH


class AIPostureDetector:
    def __init__(self, model_path: Optional[Path] = None):
        path = model_path or ensure_model_downloaded()
        options = vision.PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(path)),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
        )
        self._landmarker = vision.PoseLandmarker.create_from_options(options)
        self._start_time = time.monotonic()

    def detect(self, frame_bgr: np.ndarray) -> Optional[PostureReading]:
        frame_rgb = np.ascontiguousarray(frame_bgr[:, :, ::-1])
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        timestamp_ms = int((time.monotonic() - self._start_time) * 1000)
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)

        if not result.pose_landmarks:
            return None

        raw = result.pose_landmarks[0]
        landmarks = [ang.Landmark(lm.x, lm.y, lm.visibility) for lm in raw]

        neck_angle = ang.neck_forward_angle(landmarks)
        shoulder_metric = ang.shoulder_slouch_metric(landmarks)
        scale_px = ang.shoulder_width_px(landmarks, frame_bgr.shape[1])

        if neck_angle is None or shoulder_metric is None or scale_px is None:
            return None

        return PostureReading(
            neck_angle=neck_angle,
            shoulder_metric=shoulder_metric,
            scale_px=scale_px,
        )

    def close(self) -> None:
        self._landmarker.close()
