"""Optional on-screen live preview (toggle via config.json:
"debug_preview_enabled") so posture detection can be watched happening in
real time, instead of only during calibration.

The annotated frame is shown transiently via cv2.imshow and never written to
disk or transmitted — same privacy constraint as the rest of the pipeline.
"""
from __future__ import annotations

from typing import Optional

import cv2
import numpy as np

from .config import CalibrationData, Settings
from .detectors.base import PostureDetector, PostureReading
from .posture_state import PostureState

WINDOW_NAME = "Escapula - vista en vivo"

_BORDER_COLORS_BGR = {
    PostureState.GOOD: (46, 204, 113),
    PostureState.SUSPECT: (15, 196, 241),
    PostureState.ALERTED: (60, 76, 231),
    PostureState.UNKNOWN: (166, 165, 149),
}


class DebugPreview:
    def __init__(self):
        self._open = False

    def show(
        self,
        frame_bgr: np.ndarray,
        detector: PostureDetector,
        reading: Optional[PostureReading],
        calibration: Optional[CalibrationData],
        settings: Settings,
        state: PostureState,
        bad_since_elapsed: Optional[float],
    ) -> None:
        self._open = True
        annotated = detector.draw_debug(frame_bgr)

        lines = [f"Estado: {state.value.upper()}"]
        if calibration is not None and reading is not None:
            neck_threshold = calibration.good_neck_angle + calibration.neck_tolerance
            shoulder_threshold = calibration.good_shoulder_angle + calibration.shoulder_tolerance
            lines.append(f"Cuello: {reading.neck_angle:.1f} (limite {neck_threshold:.1f})")
            lines.append(
                f"Hombros: {reading.shoulder_metric:.1f} (limite {shoulder_threshold:.1f})"
            )
        elif reading is None:
            lines.append("Sin lectura (nadie visible / gate de distancia)")

        if bad_since_elapsed is not None:
            lines.append(
                f"Mala postura hace {bad_since_elapsed:.1f}s "
                f"/ {settings.bad_posture_hold_seconds:.0f}s"
            )

        y = 25
        for line in lines:
            cv2.putText(
                annotated, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3
            )
            cv2.putText(
                annotated, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1
            )
            y += 24

        h, w = annotated.shape[:2]
        border_color = _BORDER_COLORS_BGR[state]
        cv2.rectangle(annotated, (0, 0), (w - 1, h - 1), border_color, 6)

        cv2.imshow(WINDOW_NAME, annotated)
        cv2.waitKey(1)

    def close(self) -> None:
        if self._open:
            cv2.destroyWindow(WINDOW_NAME)
            self._open = False
