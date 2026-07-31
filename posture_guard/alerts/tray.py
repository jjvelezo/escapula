"""System tray icon: the discreet, always-visible early cue.

Color reflects the current PostureState before any toast fires, so the
user gets a non-intrusive signal first. Runs its own event loop in a
background thread via pystray.
"""
from __future__ import annotations

import threading
from typing import Callable, Dict, Literal

import pystray
from PIL import Image, ImageDraw

TrayState = Literal["good", "suspect", "alerted", "unknown", "paused"]

_COLORS: Dict[str, tuple] = {
    "good": (46, 204, 113),
    "suspect": (241, 196, 15),
    "alerted": (231, 76, 60),
    "unknown": (149, 165, 166),
    "paused": (52, 73, 94),
}

_LABELS: Dict[str, str] = {
    "good": "Buena postura",
    "suspect": "Postura dudosa",
    "alerted": "Encorvado - corrige tu postura",
    "unknown": "Sin deteccion",
    "paused": "Pausado",
}


def _make_icon_image(color: tuple) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((8, 8, 56, 56), fill=color)
    return img


class TrayController:
    def __init__(
        self,
        on_pause_toggle: Callable[[bool], None],
        on_recalibrate: Callable[[], None],
        on_quit: Callable[[], None],
        blink_interval_seconds: float = 0.5,
    ):
        self._on_pause_toggle = on_pause_toggle
        self._on_recalibrate = on_recalibrate
        self._on_quit = on_quit
        self._blink_interval_seconds = blink_interval_seconds
        self._paused = False
        self._icons = {state: _make_icon_image(color) for state, color in _COLORS.items()}
        self._icons["off"] = Image.new("RGBA", (64, 64), (0, 0, 0, 0))

        menu = pystray.Menu(
            pystray.MenuItem(self._pause_label, self._handle_pause_toggle),
            pystray.MenuItem("Recalibrar", self._handle_recalibrate),
            pystray.MenuItem("Salir", self._handle_quit),
        )
        self.icon = pystray.Icon("escapula", self._icons["unknown"], "Escapula", menu)

        self._current_state: TrayState = "unknown"
        self._stop_event = threading.Event()
        self._blink_thread = threading.Thread(target=self._blink_loop, daemon=True)

    def _pause_label(self, item) -> str:
        return "Reanudar" if self._paused else "Pausar"

    def _handle_pause_toggle(self, icon, item) -> None:
        self._paused = not self._paused
        self._on_pause_toggle(self._paused)
        self.set_state("paused" if self._paused else "unknown")

    def _handle_recalibrate(self, icon, item) -> None:
        self._on_recalibrate()

    def _handle_quit(self, icon, item) -> None:
        self._on_quit()
        self.icon.stop()

    def set_state(self, state: TrayState) -> None:
        self._current_state = state
        self.icon.title = f"Escapula - {_LABELS[state]}"
        if state != "alerted":
            self.icon.icon = self._icons[state]

    def _blink_loop(self) -> None:
        blink_on = True
        while not self._stop_event.is_set():
            if self._current_state == "alerted":
                self.icon.icon = self._icons["alerted"] if blink_on else self._icons["off"]
                blink_on = not blink_on
            self._stop_event.wait(self._blink_interval_seconds)

    def run_detached(self) -> threading.Thread:
        thread = threading.Thread(target=self.icon.run, daemon=True)
        thread.start()
        self._blink_thread.start()
        return thread

    def stop(self) -> None:
        self._stop_event.set()
        self.icon.stop()
