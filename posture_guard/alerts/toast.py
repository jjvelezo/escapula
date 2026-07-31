"""Windows toast notifications with sound and a cooldown so a long
uninterrupted slouch doesn't spam a toast every loop tick.
"""
from __future__ import annotations

from typing import Optional

from winotify import Notification, audio


class ToastNotifier:
    def __init__(self, cooldown_seconds: float = 300.0, app_id: str = "Escapula"):
        self.cooldown_seconds = cooldown_seconds
        self.app_id = app_id
        self._last_notified: Optional[float] = None

    def notify_bad_posture(self, now: float, sustained_seconds: float) -> bool:
        """Show a toast if the cooldown has elapsed. Returns True if shown."""
        if self._last_notified is not None and (now - self._last_notified) < self.cooldown_seconds:
            return False
        self._last_notified = now
        toast = Notification(
            app_id=self.app_id,
            title="Corrige tu postura",
            msg=f"Llevas encorvado {int(sustained_seconds)}s. Enderezate.",
            duration="short",
        )
        toast.set_audio(audio.Default, loop=False)
        toast.show()
        return True

    def reset(self) -> None:
        """Call when leaving ALERTED, so the next ALERTED entry notifies
        immediately instead of waiting out a stale cooldown."""
        self._last_notified = None
