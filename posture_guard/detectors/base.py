"""Shared interface both detection backends (AI and heuristic) implement.

Downstream code (calibration, posture_state, alerts) only ever sees a
PostureReading — it never knows whether the reading came from full pose
landmarks or a simple face bounding box. This is what makes the two modes
directly comparable on the same alerting logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

import numpy as np


@dataclass
class PostureReading:
    neck_angle: float
    """Degrees of forward head tilt from vertical. 0 = ear directly above
    shoulder (AI mode) or face centered/upright (heuristic mode). Larger =
    more forward lean."""

    shoulder_metric: float
    """Secondary slouch signal: shoulder-line tilt + torso collapse (AI mode)
    or face vertical-position drop + squash ratio (heuristic mode)."""

    scale_px: float
    """A distance proxy in pixels (shoulder width or face width) used for the
    distance sanity gate — large deviations from the calibrated reference
    mean the user moved/leaned in a way that makes this frame unreliable."""


class PostureDetector(Protocol):
    def detect(self, frame_bgr: np.ndarray) -> Optional[PostureReading]:
        """Return a PostureReading for this frame, or None if no person/face
        was confidently detected."""
        ...

    def close(self) -> None:
        """Release any underlying model/resources."""
        ...
