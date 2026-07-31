"""Webcam capture with Windows-friendly backend and frame throttling."""
from __future__ import annotations

import time
from typing import Iterator, Optional

import cv2
import numpy as np


class WebcamCapture:
    def __init__(self, camera_index: int = 0, frame_interval_seconds: float = 0.5):
        self.camera_index = camera_index
        self.frame_interval_seconds = frame_interval_seconds
        self._cap: Optional[cv2.VideoCapture] = None

    def open(self) -> None:
        self._cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self._cap.isOpened():
            raise RuntimeError(
                f"Could not open webcam at index {self.camera_index}."
            )

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def read(self) -> Optional[np.ndarray]:
        """Read a single current frame (BGR), or None if capture failed."""
        if self._cap is None:
            raise RuntimeError("WebcamCapture is not open. Call open() first.")
        ok, frame = self._cap.read()
        if not ok:
            return None
        return frame

    def frames(self) -> Iterator[np.ndarray]:
        """Yield frames throttled to roughly frame_interval_seconds apart.

        Drains the camera buffer each tick (grab-only) so the frame actually
        returned is fresh, not a stale buffered one from before the sleep.
        """
        if self._cap is None:
            raise RuntimeError("WebcamCapture is not open. Call open() first.")
        while True:
            start = time.monotonic()
            ok, frame = self._cap.read()
            if ok:
                yield frame
            elapsed = time.monotonic() - start
            remaining = self.frame_interval_seconds - elapsed
            if remaining > 0:
                time.sleep(remaining)

    def __enter__(self) -> "WebcamCapture":
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
