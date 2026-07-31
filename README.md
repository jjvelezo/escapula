# Escapula

![Python](https://img.shields.io/badge/python-3.11-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Windows-0078D6?logo=windows&logoColor=white)
![MediaPipe](https://img.shields.io/badge/AI-MediaPipe%20Pose%20Landmarker-orange)
![OpenCV](https://img.shields.io/badge/CV-OpenCV-5C3EE8?logo=opencv&logoColor=white)
![Privacy](https://img.shields.io/badge/privacy-100%25%20local-brightgreen)

Escapula is a lightweight Windows background utility that watches you through
your webcam and nudges you when you slouch or let your head creep forward for
too long. It lives in the system tray, stays quiet during normal movement,
and only interrupts you with a Windows toast notification once bad posture
has been genuinely sustained.

It's a personal project being run side-by-side against an iPhone/AirPods-based
posture app (Posture Pal), to see whether a webcam-based approach on Windows
is a viable/better alternative. This repo only covers the webcam side.

## Why it exists

Sitting at a desk for long stretches easily turns into slouching or leaning
the head forward without noticing. Escapula's goal is to catch that pattern
early and give a lightweight nudge to sit up straight — without being noisy,
without false-alarming on brief movements (reaching for something, glancing
down), and without ever sending your webcam feed anywhere.

**Privacy is a hard constraint, not an afterthought.** Webcam frames are only
ever held in memory — never written to disk, never transmitted over the
network. Only derived numbers (joint angles, bounding-box geometry) leave the
capture/detection code. All AI inference runs 100% locally on your machine;
there is no cloud API call anywhere in this app.

## How it works

Escapula is a simple pipeline: `webcam frame → posture reading → smoothed
state → alert`. Each stage exists to solve one specific problem.

```
 Webcam (2fps)  →  Detector  →  Smoothing/Hysteresis  →  Tray + Toast
   capture.py    ai/heuristic     posture_state.py       alerts/
```

### 1. Capture

Frames are grabbed at a low, throttled rate (~2fps by default). Posture
changes slowly, and this is meant to sit quietly in the background — no
reason to burn CPU or battery watching video at 30fps to detect something
that changes over minutes, not milliseconds.

### 2. Detect — two swappable backends

Turning a frame into a "how's your posture right now" reading is the one part
of the pipeline that's genuinely hard, so Escapula ships two interchangeable
approaches and lets you A/B them:

- **AI mode** uses [MediaPipe's Pose Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker),
  a 33-point body pose model, to compute real neck and shoulder angles.

  <img src="https://mediapipe.dev/images/mobile/pose_tracking_full_body_landmarks.png" alt="MediaPipe Pose Landmarker's 33 body landmarks" width="480">

  *The 33 landmarks MediaPipe tracks per frame (image: Google MediaPipe).
  Escapula only uses the shoulder/ear/hip points to compute posture angles —
  the rest is discarded.*

  The model runs fully offline through MediaPipe's bundled CPU runtime
  (TFLite + XNNPACK). It's downloaded once, on first run, from Google's
  public model bucket, cached in `models/`, and never touched again — after
  that it works with no internet connection at all.

- **Heuristic mode** is a zero-ML fallback: OpenCV's built-in Haar cascade
  face detector plus simple bounding-box geometry (vertical position,
  height/width ratio) as a cruder proxy for posture. No model download, no
  inference cost — useful as a baseline to compare the AI mode against.

### 3. Calibrate

Everyone's "good posture" looks different — a short console wizard (with a
live camera preview) captures your own baseline the first time you run the
app, so thresholds are personal rather than one-size-fits-all.

### 4. Smooth and debounce — why it doesn't nag you

This is the part that makes Escapula usable instead of annoying. Two layers
of filtering sit between "the detector saw something" and "you get
interrupted":

1. A **sliding-window majority vote** smooths out per-frame jitter (a single
   noisy frame doesn't flip your state).
2. A `GOOD → SUSPECT → ALERTED` **hysteresis state machine** requires bad
   posture to be *sustained* for a while (~20s by default) before alerting,
   but only requires good posture to persist briefly (~5s) before clearing
   the alert.

That asymmetry is deliberate: leaning down for a few seconds to grab
something off your desk should never trigger a notification, but genuinely
slouching for 20+ seconds should.

### 5. Alert

- A **system tray icon** changes color (green → amber → red) as an early,
  non-intrusive signal of your current state.
- A **Windows toast notification** (with sound) fires once bad posture is
  confirmed, with a cooldown so a long uninterrupted slouch doesn't spam you
  with repeat notifications.

## Installing and running it

Requires **Python 3.11** specifically — MediaPipe's PyPI wheels don't yet
support 3.13, so the virtualenv must be created with 3.11 explicitly even if
you have a newer interpreter installed too.

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python escapula.py
```

On first run:

1. A short calibration wizard opens with a live camera preview — sit in your
   normal "good" posture and follow the on-screen prompts.
2. Once calibrated, Escapula minimizes to the system tray and starts
   watching. The tray icon color tells you the current state at a glance;
   a toast notification appears if bad posture is sustained.

Switch between AI and heuristic detection by editing `mode` in
`%APPDATA%\PostureGuard\config.json` (this file also stores your calibration
baseline and the timing thresholds described above — there's no separate
settings UI yet, so it's the settings UI for now).

## Project layout

| Path | Responsibility |
|---|---|
| `escapula.py` | Entry point |
| `posture_guard/app.py` | Composition root — wires the pipeline together |
| `posture_guard/capture.py` | Webcam loop |
| `posture_guard/detectors/ai_detector.py` | MediaPipe Pose Landmarker backend |
| `posture_guard/detectors/heuristic_detector.py` | OpenCV Haar cascade backend |
| `posture_guard/angles.py` | Neck/shoulder angle math for AI mode |
| `posture_guard/calibration.py` | Console + camera-preview calibration wizard |
| `posture_guard/posture_state.py` | Smoothing + hysteresis state machine |
| `posture_guard/alerts/tray.py` | System tray icon |
| `posture_guard/alerts/toast.py` | Windows toast notifications |
| `posture_guard/config.py` | Settings/calibration persistence |

No build step, linter, or test suite is configured yet — this is a small
single-developer utility.
