"""Heuristic-mode detector: no ML model at all.

Uses OpenCV's classic Haar cascade face detector (ships built into
opencv-python, nothing to download) and infers a crude posture proxy from
face bounding-box geometry alone — no true skeletal angles. This is the
intentional trade-off point for the user's own with-AI vs without-AI
comparison: near-zero CPU cost and zero ML dependency, at the cost of being
more sensitive to lighting, hair, and glasses, and not distinguishing head
lean from shoulder slump.

Produces a PostureReading with the same shape as ai_detector so both modes
share the calibration/smoothing/alerting pipeline unchanged.
"""
from __future__ import annotations

import math
from typing import Optional

import cv2
import numpy as np

from .base import PostureReading


class HeuristicPostureDetector:
    def __init__(self):
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._face_cascade = cv2.CascadeClassifier(cascade_path)
        if self._face_cascade.empty():
            raise RuntimeError(f"Failed to load Haar cascade from {cascade_path}")

    def detect(self, frame_bgr: np.ndarray) -> Optional[PostureReading]:
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        faces = self._face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
        )
        if len(faces) == 0:
            return None

        # Largest detected face = the one closest to the camera (the user).
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        frame_h, frame_w = frame_bgr.shape[:2]

        face_center_x = x + w / 2
        face_center_y = y + h / 2

        # Forward-lean proxy: as a person leans toward the camera/screen and
        # drops their head, the face center tends to move down and the face
        # grows in the frame. We express vertical displacement from the
        # frame's vertical center as a pseudo-angle so it's on a similar
        # numeric scale to the AI mode's degree-based neck_angle, even
        # though it isn't a true skeletal angle.
        vertical_offset = face_center_y - (frame_h / 2)
        neck_angle = math.degrees(math.atan2(abs(vertical_offset), h + 1e-6))

        # Slouch proxy: face bounding-box aspect ratio deviates from a
        # roughly-square upright face as the head tilts forward/down, plus
        # how far the face has descended toward the bottom of the frame.
        aspect_ratio = w / (h + 1e-6)
        descent_ratio = face_center_y / frame_h
        shoulder_metric = abs(aspect_ratio - 1.0) * 40.0 + descent_ratio * 20.0

        return PostureReading(
            neck_angle=neck_angle,
            shoulder_metric=shoulder_metric,
            scale_px=float(w),
        )

    def close(self) -> None:
        pass
