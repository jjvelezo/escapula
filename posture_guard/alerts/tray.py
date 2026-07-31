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
    ):
        self._on_pause_toggle = on_pause_toggle
        self._on_recalibrate = on_recalibrate
        self._on_quit = on_quit
        self._paused = False
        self._icons = {state: _make_icon_image(color) for state, color in _COLORS.items()}

        menu = pystray.Menu(
            pystray.MenuItem(self._pause_label, self._handle_pause_toggle),
            pystray.MenuItem("Recalibrar", self._handle_recalibrate),
            pystray.MenuItem("Salir", self._handle_quit),
        )
        self.icon = pystray.Icon("escapula", self._icons["unknown"], "Escapula", menu)

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
        self.icon.icon = self._icons[state]
        self.icon.title = f"Escapula - {_LABELS[state]}"

    def run_detached(self) -> threading.Thread:
        thread = threading.Thread(target=self.icon.run, daemon=True)
        thread.start()
        return thread

    def stop(self) -> None:
        self.icon.stop()
