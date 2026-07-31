"""Composition root: wires capture -> detector -> state machine -> alerts.

Runs entirely on the main thread except the tray icon (pystray owns its own
thread). Tray menu actions (pause/recalibrate/quit) just flip flags on a
shared AppControl object that the main loop checks each tick — this keeps
webcam access and OpenCV windows confined to a single thread, avoiding any
cross-thread capture/GUI races.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from . import config
from .alerts.tray import TrayController
from .alerts.toast import ToastNotifier
from .calibration import run_calibration
from .capture import WebcamCapture
from .detectors.ai_detector import AIPostureDetector
from .detectors.heuristic_detector import HeuristicPostureDetector
from .posture_state import PostureState, PostureStateMachine


@dataclass
class AppControl:
    paused: bool = False
    recalibrate_requested: bool = False
    quit_requested: bool = False


def _make_detector(mode: str):
    if mode == "ai":
        return AIPostureDetector()
    if mode == "heuristic":
        return HeuristicPostureDetector()
    raise ValueError(f"Unknown detection mode: {mode!r}")


_STATE_TO_TRAY = {
    PostureState.GOOD: "good",
    PostureState.SUSPECT: "suspect",
    PostureState.ALERTED: "alerted",
    PostureState.UNKNOWN: "unknown",
}


def run() -> None:
    settings = config.load_settings()
    print(f"Escapula starting in '{settings.mode}' mode.")

    detector = _make_detector(settings.mode)
    control = AppControl()

    with WebcamCapture(frame_interval_seconds=settings.frame_interval_seconds) as cap:
        if settings.calibration is None:
            print("Primera ejecucion: iniciando calibracion...")
            settings.calibration = run_calibration(detector, cap, settings)
            config.save_settings(settings)

        state_machine = PostureStateMachine(settings, settings.calibration)
        toast_notifier = ToastNotifier(cooldown_seconds=settings.toast_cooldown_seconds)

        def on_pause_toggle(paused: bool) -> None:
            control.paused = paused
            print("Pausado." if paused else "Reanudado.")

        def on_recalibrate() -> None:
            control.recalibrate_requested = True

        def on_quit() -> None:
            control.quit_requested = True

        tray = None
        if settings.tray_enabled:
            tray = TrayController(on_pause_toggle, on_recalibrate, on_quit)
            tray.run_detached()

        previous_state = PostureState.UNKNOWN
        try:
            for frame in cap.frames():
                if control.quit_requested:
                    break

                if control.recalibrate_requested:
                    control.recalibrate_requested = False
                    print("Recalibrando...")
                    settings.calibration = run_calibration(detector, cap, settings)
                    config.save_settings(settings)
                    state_machine = PostureStateMachine(settings, settings.calibration)
                    previous_state = PostureState.UNKNOWN
                    continue

                if control.paused:
                    continue

                now = time.monotonic()
                reading = detector.detect(frame)
                state = state_machine.update(reading, now)

                if tray is not None:
                    tray.set_state(_STATE_TO_TRAY[state])

                if state == PostureState.ALERTED:
                    sustained = now - (state_machine.bad_since or now)
                    if settings.toast_enabled:
                        toast_notifier.notify_bad_posture(now, sustained)
                elif previous_state == PostureState.ALERTED:
                    toast_notifier.reset()

                previous_state = state
        except KeyboardInterrupt:
            pass
        finally:
            detector.close()
            if tray is not None:
                tray.stop()

    print("Escapula stopped.")
