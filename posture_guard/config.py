"""Settings and calibration persistence in config.jsonc at the project root.

The file is JSON with // comments (JSONC) so it can document itself: it is
the app's only settings UI. save_settings() regenerates it from the Settings
fields plus _COMMENTS/_SECTIONS below, so comments survive every rewrite.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Literal, Optional

Mode = Literal["ai", "heuristic"]


PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Older locations, read once for migration if config.jsonc doesn't exist yet.
_LEGACY_PATHS = (
    PROJECT_ROOT / "config.json",
    Path(os.getenv("APPDATA", str(Path.home()))) / "PostureGuard" / "config.json",
)


def config_path() -> Path:
    return PROJECT_ROOT / "config.jsonc"


@dataclass
class CalibrationData:
    good_neck_angle: float
    good_shoulder_angle: float
    neck_tolerance: float
    shoulder_tolerance: float
    reference_distance: float


@dataclass
class Settings:
    # --- Common options (the ones you'll most likely want to change) ---
    mode: Mode = "ai"
    camera_index: int = 0
    tray_enabled: bool = True
    toast_enabled: bool = True
    toast_sound_enabled: bool = True
    sound_alert_enabled: bool = True
    debug_preview_enabled: bool = False
    bad_posture_hold_seconds: float = 10.0

    # --- Alert tuning ---
    toast_cooldown_seconds: float = 300.0
    toast_duration: str = "short"
    sound_alert_interval_seconds: float = 8.0
    sound_alert_frequency_hz: int = 880
    sound_alert_duration_ms: int = 250
    tray_blink_interval_seconds: float = 0.5

    # --- Advanced: posture_state.py smoothing/hysteresis ---
    good_posture_release_seconds: float = 5.0
    smoothing_window_seconds: float = 2.0
    smoothing_bad_vote_ratio: float = 0.6
    distance_gate_ratio: float = 0.4

    # --- Advanced: capture.py ---
    frame_interval_seconds: float = 0.5

    # --- Advanced: calibration.py ---
    calibration_num_samples: int = 10
    calibration_tolerance_ratio: float = 0.35
    calibration_min_neck_tolerance: float = 8.0
    calibration_min_shoulder_tolerance: float = 5.0
    default_neck_tolerance: float = 12.0
    default_shoulder_tolerance: float = 8.0

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


# Header printed before the first field of each group.
_SECTIONS = {
    "mode": "OPCIONES PRINCIPALES",
    "toast_cooldown_seconds": "AJUSTES DE LAS ALERTAS",
    "good_posture_release_seconds": "AVANZADO: deteccion y suavizado (normalmente no hace falta tocarlo)",
    "calibration_num_samples": "AVANZADO: calibracion",
    "calibration": "TU CALIBRACION (se genera sola)",
}

_COMMENTS = {
    "mode": 'Deteccion: "ai" (modelo MediaPipe, mas preciso) o "heuristic" (solo cara, sin modelo). Recalibra si lo cambias.',
    "camera_index": "Camara a usar: 0 = la principal. Prueba 1, 2... si tienes varias.",
    "tray_enabled": "Icono de color en la bandeja del sistema (verde / ambar / rojo).",
    "toast_enabled": "Notificacion de Windows cuando llevas un rato encorvado.",
    "toast_sound_enabled": "Sonido de la notificacion (false = notificacion silenciosa).",
    "sound_alert_enabled": "Pitido que se repite mientras sigas encorvado.",
    "debug_preview_enabled": "Ventana en vivo con lo que ve la camara (esqueleto, angulos, estado). No guarda nada.",
    "bad_posture_hold_seconds": "Segundos de mala postura antes de alertar. Subelo si te avisa demasiado.",
    "toast_cooldown_seconds": "Minimo de segundos entre dos notificaciones.",
    "toast_duration": 'Tiempo en pantalla de la notificacion: "short" (~5 s) o "long" (~25 s).',
    "sound_alert_interval_seconds": "Segundos entre pitidos.",
    "sound_alert_frequency_hz": "Tono del pitido en Hz (37 a 32767).",
    "sound_alert_duration_ms": "Duracion de cada pitido en milisegundos.",
    "tray_blink_interval_seconds": "Velocidad del parpadeo del icono rojo.",
    "good_posture_release_seconds": "Segundos de buena postura para quitar la alerta.",
    "smoothing_window_seconds": "Ventana (s) en la que se votan los fotogramas para filtrar ruido.",
    "smoothing_bad_vote_ratio": "Fraccion de fotogramas 'malos' en esa ventana para considerarla mala postura.",
    "distance_gate_ratio": "Ignora lecturas si estas esta fraccion mas cerca/lejos que al calibrar.",
    "frame_interval_seconds": "Segundos entre fotogramas analizados (0.5 = 2 por segundo). Mas alto = menos CPU.",
    "calibration_num_samples": "Muestras que toma la calibracion en cada paso.",
    "calibration_tolerance_ratio": "Que tan cerca de tu postura 'mala' se pone el limite (0 a 1).",
    "calibration_min_neck_tolerance": "Tolerancia minima del cuello (grados).",
    "calibration_min_shoulder_tolerance": "Tolerancia minima de los hombros.",
    "default_neck_tolerance": "Tolerancia del cuello si omites el paso de postura mala.",
    "default_shoulder_tolerance": "Tolerancia de los hombros si omites el paso de postura mala.",
    "calibration": "Tu calibracion guardada. Ponlo en null para recalibrar al iniciar (o usa 'Recalibrar' en el icono).",
}


def _strip_comments(text: str) -> str:
    """Remove // comments outside of strings."""
    out = []
    in_string = escaped = False
    i = 0
    while i < len(text):
        c = text[i]
        if in_string:
            out.append(c)
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                in_string = False
        elif c == '"':
            in_string = True
            out.append(c)
        elif text.startswith("//", i):
            while i < len(text) and text[i] != "\n":
                i += 1
            continue
        else:
            out.append(c)
        i += 1
    return "".join(out)


def load_settings() -> Settings:
    path = config_path()
    if not path.exists():
        path = next((p for p in _LEGACY_PATHS if p.exists()), None)
        if path is None:
            return Settings()
    text = path.read_text(encoding="utf-8")
    try:
        return Settings.from_dict(json.loads(_strip_comments(text)))
    except json.JSONDecodeError as e:
        # Refuse to start rather than fall back to defaults: the caller saves
        # right after loading, which would wipe the user's edits/calibration.
        raise SystemExit(
            f"Error en {path.name}, linea {e.lineno}: {e.msg}.\n"
            "Revisa comas y comillas, o borra el archivo para regenerarlo."
        ) from None


def save_settings(settings: Settings) -> None:
    lines = [
        "// Configuracion de Escapula.",
        "// Cierra la app antes de editar y vuelve a abrirla para aplicar los cambios.",
        "// true = activado, false = desactivado.",
        "{",
    ]
    data = settings.to_dict()
    for name, value in data.items():
        if name in _SECTIONS:
            if len(lines) > 4:
                lines.append("")
            lines.append(f"  // ===== {_SECTIONS[name]} =====")
        lines.append(f"  // {_COMMENTS[name]}")
        rendered = json.dumps(value, indent=2).replace("\n", "\n  ")
        comma = "," if name != "calibration" else ""
        lines.append(f'  "{name}": {rendered}{comma}')
    lines.append("}")
    config_path().write_text("\n".join(lines) + "\n", encoding="utf-8")
