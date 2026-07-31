"""The false-positive defense: smoothing + hysteresis state machine.

Turns a noisy per-frame PostureReading stream into a stable GOOD / SUSPECT /
ALERTED state, deliberately biased so a brief lean-down to grab something
(a few seconds) never reaches ALERTED, while genuine sustained bad posture
does. Pure logic, no I/O — testable with synthetic timestamped sequences.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Deque, Optional, Tuple

from .config import CalibrationData, Settings
from .detectors.base import PostureReading


class PostureState(Enum):
    GOOD = "good"
    SUSPECT = "suspect"
    ALERTED = "alerted"
    UNKNOWN = "unknown"  # no reliable reading yet (no person / distance gate)


def frame_is_bad(
    reading: Optional[PostureReading],
    calibration: Optional[CalibrationData],
    settings: Settings,
) -> Optional[bool]:
    """Classify a single frame as bad-posture True/False, or None if the
    frame is inconclusive (no person, or the distance sanity gate rejects
    it — e.g. the user leaned sharply toward/away from the camera)."""
    if reading is None:
        return None

    if calibration is not None:
        if calibration.reference_distance > 0:
            deviation = abs(reading.scale_px - calibration.reference_distance) / calibration.reference_distance
            if deviation > settings.distance_gate_ratio:
                return None
        neck_threshold = calibration.good_neck_angle + calibration.neck_tolerance
        shoulder_threshold = calibration.good_shoulder_angle + calibration.shoulder_tolerance
    else:
        neck_threshold = settings.default_neck_tolerance
        shoulder_threshold = settings.default_shoulder_tolerance

    neck_bad = reading.neck_angle > neck_threshold
    shoulder_bad = reading.shoulder_metric > shoulder_threshold
    return neck_bad or shoulder_bad


class PostureStateMachine:
    def __init__(self, settings: Settings, calibration: Optional[CalibrationData]):
        self.settings = settings
        self.calibration = calibration
        self._window: Deque[Tuple[float, Optional[bool]]] = deque()
        self.state = PostureState.UNKNOWN
        self.bad_since: Optional[float] = None
        self.good_since: Optional[float] = None

    def _smoothed_is_bad(self, now: float) -> Optional[bool]:
        """Majority vote over the trailing smoothing window, ignoring
        inconclusive (None) frames. None if no conclusive samples exist."""
        cutoff = now - self.settings.smoothing_window_seconds
        while self._window and self._window[0][0] < cutoff:
            self._window.popleft()

        votes = [v for _, v in self._window if v is not None]
        if not votes:
            return None
        bad_fraction = sum(votes) / len(votes)
        return bad_fraction >= 0.6

    def update(self, reading: Optional[PostureReading], now: float) -> PostureState:
        raw_bad = frame_is_bad(reading, self.calibration, self.settings)
        self._window.append((now, raw_bad))
        smoothed = self._smoothed_is_bad(now)

        if smoothed is None:
            # No conclusive recent signal — don't flip state on missing data,
            # but do let a long enough silence decay ALERTED/SUSPECT back to
            # UNKNOWN so a permanently-empty chair doesn't stay "alerted".
            if self.state in (PostureState.SUSPECT, PostureState.ALERTED):
                cutoff = now - max(
                    self.settings.bad_posture_hold_seconds,
                    self.settings.good_posture_release_seconds,
                )
                if all(t < cutoff for t, _ in self._window) or not self._window:
                    self.state = PostureState.UNKNOWN
                    self.bad_since = None
                    self.good_since = None
            return self.state

        if smoothed:
            self.good_since = None
            if self.bad_since is None:
                self.bad_since = now
            if self.state in (PostureState.GOOD, PostureState.UNKNOWN):
                self.state = PostureState.SUSPECT
            if self.state == PostureState.SUSPECT:
                held_for = now - self.bad_since
                if held_for >= self.settings.bad_posture_hold_seconds:
                    self.state = PostureState.ALERTED
        else:
            self.bad_since = None
            if self.good_since is None:
                self.good_since = now
            if self.state in (PostureState.SUSPECT, PostureState.ALERTED):
                held_for = now - self.good_since
                if held_for >= self.settings.good_posture_release_seconds:
                    self.state = PostureState.GOOD
            elif self.state == PostureState.UNKNOWN:
                self.state = PostureState.GOOD

        return self.state
