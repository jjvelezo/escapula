# Escapula

Escapula is a lightweight Windows background utility that watches you through
your webcam and nudges you when you slouch or let your head creep forward for
too long. It lives in the system tray, stays quiet during normal movement,
and only interrupts you with a Windows toast notification once bad posture
has been genuinely sustained.

It's a personal project being run side-by-side against an iPhone/AirPods-based
posture app (Posture Pal), to see whether a webcam-based approach on Windows
is a viable/better alternative. This repo only covers the webcam side.

## Objective

Sitting at a desk for long stretches easily turns into slouching or leaning
the head forward without noticing. Escapula's goal is to catch that pattern
early and give a lightweight nudge to sit up — without being noisy, without
false-alarming on brief movements (reaching for something, glancing down),
and without ever sending your webcam feed anywhere.

**Privacy is a hard constraint, not an afterthought:** webcam frames are only
ever held in memory. They are never written to disk or transmitted over the
network. Only derived numbers (angles, bounding-box geometry) leave the
capture/detection code. All AI inference runs 100% locally on your machine —
there is no cloud API call anywhere in this app.

## How it works

1. **Capture** — grabs frames from your webcam at a low rate (~2fps by
   default), since posture changes slowly and this is meant to run quietly
   in the background without burning CPU.

2. **Detect** — turns each frame into a posture reading. Escapula ships with
   two interchangeable detection backends so they can be compared for
   real-world effectiveness:
   - **AI mode** — uses MediaPipe's on-device Pose Landmarker (a 33-point
     body pose model) to compute actual neck and shoulder angles. The model
     runs fully offline through MediaPipe's bundled CPU runtime; it's
     downloaded once from Google's public model bucket on first run and
     cached locally.
   - **Heuristic mode** — a zero-ML-dependency fallback using OpenCV's
     built-in face detector and simple bounding-box geometry (position,
     height/width ratio) as a cruder proxy for posture.

3. **Calibrate** — the first time you run it, a short console-driven wizard
   (with a live camera preview) captures your own "good posture" baseline,
   since what counts as good posture differs from person to person.

4. **Smooth and debounce** — per-frame readings are noisy, so a sliding-window
   majority vote smooths out jitter, and a `GOOD → SUSPECT → ALERTED` state
   machine requires bad posture to be sustained for a while (~20s by default)
   before alerting, while requiring good posture to persist (~5s) before
   clearing the alert. This asymmetry means a quick lean to grab something
   off your desk won't trigger a notification, but real slouching will.

5. **Alert** — a system tray icon changes color (green/amber/red) as an
   early, unobtrusive signal of your current state, and a Windows toast
   notification (with sound) fires once posture is confirmed bad, with a
   cooldown so it doesn't spam you during a long slouch.

Settings and your calibration baseline are stored in
`%APPDATA%\PostureGuard\config.json`, which also doubles as a hand-editable
settings file (no separate settings UI exists yet).

## Running it

Requires **Python 3.11** specifically (MediaPipe's PyPI wheels don't yet
support 3.13).

```
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python escapula.py
```

On first run you'll be walked through the calibration wizard. After that,
Escapula runs quietly in the tray, watching and alerting as described above.
