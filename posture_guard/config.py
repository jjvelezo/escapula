"""Settings and calibration persistence in %APPDATA%\\PostureGuard\\config.json."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Literal, Optional

Mode = Literal["ai", "heuristic"]


def config_dir() -> Path:
    appdata = os.getenv("APPDATA", str(Path.home()))
    d = Path(appdata) / "PostureGuard"
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path() -> Path:
    return config_dir() / "config.json"


@dataclass
class CalibrationData:
    good_neck_angle: float
    good_shoulder_angle: float
    neck_tolerance: float
    shoulder_tolerance: float
    reference_distance: float


@dataclass
class Settings:
    mode: Mode = "ai"

    # --- posture_state.py: hysteresis timing ---
    bad_posture_hold_seconds: float = 10.0
    good_posture_release_seconds: float = 5.0
    smoothing_window_seconds: float = 2.0
    smoothing_bad_vote_ratio: float = 0.6

    # --- capture.py ---
    frame_interval_seconds: float = 0.5

    # --- calibration.py ---
    calibration_num_samples: int = 10
    calibration_tolerance_ratio: float = 0.35
    calibration_min_neck_tolerance: float = 8.0
    calibration_min_shoulder_tolerance: float = 5.0
    default_neck_tolerance: float = 12.0
    default_shoulder_tolerance: float = 8.0
    distance_gate_ratio: float = 0.4

    # --- alerts/toast.py ---
    toast_enabled: bool = True
    toast_cooldown_seconds: float = 300.0
    toast_duration: str = "short"

    # --- alerts/sound.py ---
    sound_alert_enabled: bool = True
    sound_alert_interval_seconds: float = 8.0
    sound_alert_frequency_hz: int = 880
    sound_alert_duration_ms: int = 250

    # --- alerts/tray.py ---
    tray_enabled: bool = True
    tray_blink_interval_seconds: float = 0.5

    # --- debug_view.py ---
    debug_preview_enabled: bool = False

    calibration: Optional[CalibrationData] = field(default=None)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Settings":
        known_fields = {f.name for f in fields(Settings)} - {"calibration"}
        settings_kwargs = {k: v for k, v in d.items() if k in known_fields}
        s = Settings(**settings_kwargs)
        calib = d.get("calibration")
        if calib:
            s.calibration = CalibrationData(**calib)
        return s


def load_settings() -> Settings:
    path = config_path()
    if not path.exists():
        return Settings()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Settings.from_dict(data)
    except (json.JSONDecodeError, TypeError, KeyError):
        return Settings()


def save_settings(settings: Settings) -> None:
    path = config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings.to_dict(), f, indent=2)
