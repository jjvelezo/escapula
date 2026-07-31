"""Console-driven first-run calibration wizard with a live webcam preview.

Shared by both detection modes: it only depends on the mode-agnostic
PostureDetector/PostureReading interface, so calibrating in "ai" mode
and "heuristic" mode looks and works identically to the user.
"""
from __future__ import annotations

import time
from typing import List, Optional, Tuple

import cv2

from .capture import WebcamCapture
from .config import CalibrationData, Settings
from .detectors.base import PostureDetector, PostureReading

WINDOW_NAME = "Escapula - calibracion"
SPACE = 32
S_KEY = ord("s")


def _wait_for_key(cap: WebcamCapture, prompt_lines: List[str], target_keys: set) -> int:
    while True:
        frame = cap.read()
        if frame is None:
            continue
        display = frame.copy()
        y = 30
        for line in prompt_lines:
            cv2.putText(display, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            y += 30
        cv2.imshow(WINDOW_NAME, display)
        key = cv2.waitKey(30) & 0xFF
        if key in target_keys:
            return key


def _collect_average(
    detector: PostureDetector, cap: WebcamCapture, num_samples: int
) -> Optional[Tuple[float, float, float]]:
    readings: List[PostureReading] = []
    attempts = 0
    max_attempts = num_samples * 20  # avoid an infinite loop if nobody is visible
    while len(readings) < num_samples and attempts < max_attempts:
        frame = cap.read()
        attempts += 1
        if frame is None:
            continue
        cv2.putText(
            frame, f"Capturando... {len(readings)}/{num_samples}",
            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2,
        )
        cv2.imshow(WINDOW_NAME, frame)
        cv2.waitKey(1)
        reading = detector.detect(frame)
        if reading is not None:
            readings.append(reading)
        time.sleep(0.1)

    if not readings:
        return None

    neck = sum(r.neck_angle for r in readings) / len(readings)
    shoulder = sum(r.shoulder_metric for r in readings) / len(readings)
    scale = sum(r.scale_px for r in readings) / len(readings)
    return neck, shoulder, scale


def run_calibration(
    detector: PostureDetector, cap: WebcamCapture, settings: Settings
) -> CalibrationData:
    _wait_for_key(
        cap,
        [
            "Sientate en tu postura normal de trabajo.",
            "Presiona ESPACIO cuando estes listo.",
        ],
        {SPACE},
    )
    good = _collect_average(detector, cap, settings.calibration_num_samples)
    if good is None:
        cv2.destroyWindow(WINDOW_NAME)
        raise RuntimeError(
            "No se pudo detectar tu postura durante la calibracion. "
            "Verifica que la camara te vea bien e intenta de nuevo."
        )
    good_neck, good_shoulder, reference_distance = good

    key = _wait_for_key(
        cap,
        [
            "Ahora encorvate como sueles hacerlo cuando te cansas.",
            "Presiona ESPACIO para capturar, o 'S' para omitir este paso.",
        ],
        {SPACE, S_KEY},
    )

    bad = (
        _collect_average(detector, cap, settings.calibration_num_samples)
        if key == SPACE
        else None
    )

    cv2.destroyWindow(WINDOW_NAME)

    if bad is not None:
        bad_neck, bad_shoulder, _ = bad
        ratio = settings.calibration_tolerance_ratio
        neck_tolerance = max(
            settings.calibration_min_neck_tolerance, ratio * (bad_neck - good_neck)
        )
        shoulder_tolerance = max(
            settings.calibration_min_shoulder_tolerance, ratio * (bad_shoulder - good_shoulder)
        )
    else:
        neck_tolerance = settings.default_neck_tolerance
        shoulder_tolerance = settings.default_shoulder_tolerance

    calibration = CalibrationData(
        good_neck_angle=good_neck,
        good_shoulder_angle=good_shoulder,
        neck_tolerance=neck_tolerance,
        shoulder_tolerance=shoulder_tolerance,
        reference_distance=reference_distance,
    )

    print("Calibracion completa:")
    print(f"  good_neck_angle     = {calibration.good_neck_angle:.2f}")
    print(f"  good_shoulder_angle = {calibration.good_shoulder_angle:.2f}")
    print(f"  neck_tolerance      = {calibration.neck_tolerance:.2f}")
    print(f"  shoulder_tolerance  = {calibration.shoulder_tolerance:.2f}")
    print(f"  reference_distance  = {calibration.reference_distance:.2f}")

    return calibration
