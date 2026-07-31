"""Simple repeating system beep, independent of the Windows toast/notification
stack (which can be silenced by Focus Assist or notification settings)."""
from __future__ import annotations

import winsound


def play_alert_beep(frequency_hz: int, duration_ms: int) -> None:
    winsound.Beep(frequency_hz, duration_ms)
