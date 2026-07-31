"""Entry point: python escapula.py

Watches your posture through the webcam (mode configurable in
%APPDATA%\\PostureGuard\\config.json: "ai" for MediaPipe pose estimation,
"heuristic" for a no-ML face-geometry proxy) and alerts you via the system
tray icon and Windows toast notifications when you slouch for too long.
"""
from posture_guard.app import run

if __name__ == "__main__":
    run()
