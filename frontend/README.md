
# Martial Arts Movement Analyzer

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.10-5C3EE8?style=flat-square&logo=opencv&logoColor=white)](https://opencv.org/)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-Tasks_API-007A87?style=flat-square)](https://developers.google.com/mediapipe)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?style=flat-square&logo=next.js)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![CI](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?style=flat-square&logo=github-actions)](https://github.com/Aaryan-Thaker/martial-arts-movement-analyzer/actions)

A computer vision and biomechanics pipeline engineered to analyze martial arts technique execution, joint kinematic trajectories, and form consistency from video feeds.

The system combines a modular Python backend (OpenCV, MediaPipe Pose Tasks API, SciPy) with an interactive Next.js 16 training and segment-editing web interface.

---

## Key Features

- **MediaPipe 3D Landmark Tracking**: Extracts 33 full-body landmarks using the MediaPipe Pose Tasks API (`pose_landmarker_full.task`), retrieving both 2D image coordinates and true metric 3D `world_landmarks` (measured in meters).
- **1-Euro Adaptive Low-Pass Filtering**: Implements real-time temporal noise filtering across spatial coordinates to eliminate high-velocity jitter during fast strikes without introducing phase lag during static stances.
- **Aspect-Corrected & 3D Kinematics Engine**:
  - Resolves non-square aspect ratio skew by computing angles in isotropic metric or scaled pixel coordinate spaces.
  - Computes spatial joint angles (elbows, knees, hips, shoulders) via vector dot products ($\theta = \arccos\left(\frac{\mathbf{u} \cdot \mathbf{v}}{\Vert{}\mathbf{u}\Vert{} \Vert{}\mathbf{v}\Vert{}}\right)$).
  - Calculates instantaneous angular velocities ($\omega = \frac{\Delta\theta}{\Delta t}$) and limb speeds.
  - Tracks guard integrity (hand elevation relative to chin/head) and transverse torso/hip rotation.
  - Protects against tracking dropouts by resetting delta calculations across occluded frames to eliminate false velocity spikes.
- **Automated Movement Segmentation**: Evaluates kinetic energy curves, limb velocities, and stance zero-crossings to detect technique initiation, peak extension, and recovery phases.
- **H.264 Video Telemetry Overlay**: Renders real-time visual HUD overlays (joint angle arcs, velocity gauges, stance base geometry) and encodes output using browser-native H.264 (`avc1`) with graceful fallback to `mp4v`.
- **Next.js Kata Training Player & Editor**: Interactive frontend for frame-by-frame video playback, movement timeline inspection, and technique annotation.

---
```
## Project Structure

```text
martial-arts-movement-analyzer/
├── .github/
│   └── workflows/
│       └── ci.yml                     # Dual CI: Python unit tests & Next.js production build
├── martial_arts_ai/
│   ├── __init__.py                    # Public API exports
│   ├── __main__.py                    # Package execution entrypoint
│   ├── cli.py                         # Unified command-line interface (argparse)
│   ├── detector.py                    # MediaPipe Pose wrapper with 3D landmark extraction
│   ├── filters.py                     # One-Euro filter and temporal smoothing algorithms
│   ├── kinematics.py                  # 3D vector biomechanics and angle calculation engine
│   ├── segmenter.py                   # Kinetic velocity peak and hold phase segmenter
│   └── visualizer.py                  # Video telemetry HUD renderer and H.264 exporter
├── frontend/                          # Next.js 16 web application
│   ├── app/
│   │   ├── page.tsx                   # Kata catalog landing page
│   │   ├── training/page.tsx          # Interactive kata playback and technique viewer
│   │   └── editor/page.tsx            # Movement segment editor with local storage sync
│   ├── public/                        # Static assets and kata metadata
│   ├── package.json                   # Frontend dependencies and scripts
│   └── tsconfig.json                  # TypeScript configuration
├── tests/
│   ├── test_filters.py                # Unit tests for filter step response and smoothing
│   └── test_kinematics.py             # Unit tests for 3D angles, velocities, and dropout recovery
├── videos/
│   └── heian_shodan.json              # Shotokan Kata movement definition reference
├── download_model.py                  # Automated script to fetch MediaPipe model bundle
├── pyproject.toml                     # Python project configuration
├── requirements.txt                   # Pinned Python dependencies
└── .gitignore                         # Strict exclusion for binaries, videos, and node_modules

```

---

## Architecture & Data Flow

```text
Input (Video File or Live Webcam)
              │
              ▼
    [ martial_arts_ai.detector ]
      MediaPipe Tasks API Pose Landmarker
      Extracts Screen Coordinates & 3D Metric World Landmarks
              │
              ▼
    [ martial_arts_ai.filters ]
      One-Euro Adaptive Low-Pass Filter
      Eliminates High-Frequency Jitter with Zero Phase Lag
              │
              ▼
   [ martial_arts_ai.kinematics ]
      Vector Dot Product Spatial Angles & Angular Velocities (ω)
      Stance Trajectory, Guard Integrity, and Dropout Guard
              │
      ┌───────┴────────────────────────┐
      ▼                                ▼
[ segmenter.py ]               [ visualizer.py ]
Kinetic Curve Splitting        H.264 Telemetry Video Export
Technique Boundaries           Annotated Angles & Gauges
      │                                │
      └───────┬────────────────────────┘
              ▼
      [ frontend/ ]
      Next.js 16 Training Player & Timeline Editor

```

---

## Getting Started

### 1. Prerequisites

* Python 3.11+
* Node.js 20+ and npm
* Git

### 2. Installation & Setup

Clone the repository:

```bash
git clone git@github.com:Aaryan-Thaker/martial-arts-movement-analyzer.git
cd martial-arts-movement-analyzer

```

Set up the Python environment:

```bash
# Create and activate virtual environment
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate
# On Windows (Git Bash):
source .venv/Scripts/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Download the MediaPipe pose landmarker model (~9.4 MB)
python download_model.py

```

Set up the Next.js frontend:

```bash
cd frontend
npm install
cd ..

```

---

## Usage

### Offline Video Analysis

Process a target video file, compute kinematic metrics, render an annotated video with visual HUD telemetry, and export data directly to the frontend:

```bash
python -m martial_arts_ai analyze \
  --input path/to/input.mp4 \
  --output videos/pose_output.mp4 \
  --json-out videos/movement_analysis.json \
  --export-frontend

```

### Real-Time Live Webcam Telemetry

Run the live tracking pipeline directly against a connected webcam:

```bash
python -m martial_arts_ai live --webcam 0

```

### Launch the Frontend Interface

Start the Next.js web application to view and edit kata sequences:

```bash
cd frontend
npm run dev

```

Open `http://localhost:3000` in your browser.

---

## Running Tests

Unit tests validate the mathematical correctness of 3D vector angle calculations, aspect ratio normalization, filter response, and occlusion handling:

```bash
# Run unit tests with unittest
python -m unittest discover tests

# Or run with pytest
pytest -v

```

---

## Continuous Integration

Every push and pull request to `main` triggers a two-job GitHub Actions workflow:

* **Python CI**: Installs pinned dependencies and runs the complete test suite across Python 3.11.
* **Frontend CI**: Performs a clean `npm ci` and verifies the Next.js 16 / TypeScript production build.

