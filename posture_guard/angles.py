"""Pure, stateless geometry functions turning MediaPipe pose landmarks into
posture angle metrics. No I/O, no state — easy to sanity-check in isolation.
"""
from __future__ import annotations

import math
from typing import Optional, Sequence

# MediaPipe BlazePose 33-point indices we care about.
NOSE = 0
LEFT_EAR = 7
RIGHT_EAR = 8
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_HIP = 23
RIGHT_HIP = 24

VISIBILITY_THRESHOLD = 0.5


class Landmark:
    """Minimal duck-typed landmark: has .x, .y (normalized 0-1) and .visibility."""

    __slots__ = ("x", "y", "visibility")

    def __init__(self, x: float, y: float, visibility: float):
        self.x = x
        self.y = y
        self.visibility = visibility


def _visible(landmarks: Sequence[Landmark], idx: int) -> bool:
    return landmarks[idx].visibility >= VISIBILITY_THRESHOLD


def _side_neck_angle(ear: Landmark, shoulder: Landmark) -> float:
    """Angle in degrees between the shoulder->ear vector and straight-up
    vertical. 0 = ear directly above shoulder. Positive = ear forward
    (toward smaller/larger x, direction doesn't matter, we take abs)."""
    dx = ear.x - shoulder.x
    dy = shoulder.y - ear.y  # image y grows downward; flip so "up" is positive
    if dy <= 0:
        # Ear is not above shoulder at all (e.g. head tipped back/occluded) —
        # treat as maximally bad rather than dividing by a non-positive dy.
        return 90.0
    return math.degrees(math.atan2(abs(dx), dy))


def neck_forward_angle(landmarks: Sequence[Landmark]) -> Optional[float]:
    """Average neck-forward angle (degrees) over whichever ear/shoulder side
    pairs are confidently visible. None if neither side is usable."""
    readings = []
    if _visible(landmarks, LEFT_EAR) and _visible(landmarks, LEFT_SHOULDER):
        readings.append(_side_neck_angle(landmarks[LEFT_EAR], landmarks[LEFT_SHOULDER]))
    if _visible(landmarks, RIGHT_EAR) and _visible(landmarks, RIGHT_SHOULDER):
        readings.append(_side_neck_angle(landmarks[RIGHT_EAR], landmarks[RIGHT_SHOULDER]))
    if not readings:
        return None
    return sum(readings) / len(readings)


def shoulder_width_px(landmarks: Sequence[Landmark], image_width: int) -> Optional[float]:
    """Pixel distance between shoulders, used as the distance-sanity-gate scale."""
    if not (_visible(landmarks, LEFT_SHOULDER) and _visible(landmarks, RIGHT_SHOULDER)):
        return None
    dx = (landmarks[LEFT_SHOULDER].x - landmarks[RIGHT_SHOULDER].x) * image_width
    dy = (landmarks[LEFT_SHOULDER].y - landmarks[RIGHT_SHOULDER].y) * image_width
    return math.hypot(dx, dy)


def shoulder_slouch_metric(landmarks: Sequence[Landmark]) -> Optional[float]:
    """Combines shoulder-line tilt (degrees from horizontal) with a torso
    collapse ratio (nose-to-shoulder distance vs shoulder-to-hip distance,
    normalized) into a single 0-100-ish severity score. Higher = more
    slouched. Catches "sinking in the chair" that a pure neck angle misses.
    """
    have_shoulders = _visible(landmarks, LEFT_SHOULDER) and _visible(landmarks, RIGHT_SHOULDER)
    if not have_shoulders:
        return None

    ls, rs = landmarks[LEFT_SHOULDER], landmarks[RIGHT_SHOULDER]
    tilt_deg = math.degrees(math.atan2(abs(ls.y - rs.y), abs(ls.x - rs.x) + 1e-6))

    collapse_component = 0.0
    have_hips = _visible(landmarks, LEFT_HIP) and _visible(landmarks, RIGHT_HIP)
    have_nose = _visible(landmarks, NOSE)
    if have_hips and have_nose:
        shoulder_mid_y = (ls.y + rs.y) / 2
        hip_mid_y = (landmarks[LEFT_HIP].y + landmarks[RIGHT_HIP].y) / 2
        nose_y = landmarks[NOSE].y
        torso_span = hip_mid_y - shoulder_mid_y
        if torso_span > 1e-6:
            # As the user slouches/sinks, the nose drops relative to the
            # shoulder-hip span (shoulders rise toward ears, head drops).
            collapse_component = max(0.0, (shoulder_mid_y - nose_y) / torso_span) * 20.0

    return tilt_deg + collapse_component
