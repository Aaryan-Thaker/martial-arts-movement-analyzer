#!/usr/bin/env python3
"""
Legacy wrapper for pose kinematic analysis.
Uses martial_arts_ai.KinematicsEngine to compute 3D joint angles,
angular velocities, guard integrity, and torso rotation.
"""

import json
from pathlib import Path
from martial_arts_ai.kinematics import KinematicsEngine

INPUT_JSON = Path("videos/pose_data.json")
OUTPUT_JSON = Path("videos/movement_analysis.json")


def main() -> None:
    print("=" * 60)
    print(" Martial Arts Movement Analyzer - Kinematics (Modular Engine)")
    print("=" * 60)

    if not INPUT_JSON.exists():
        print(f"[Notice] {INPUT_JSON} not found. Running full analysis pipeline instead...")
        from martial_arts_ai.cli import main as cli_main
        import sys
        sys.argv = ["martial-arts-ai", "analyze"]
        cli_main()
        return

    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        pose_data = json.load(f)

    fps = pose_data.get("fps", 30.0)
    engine = KinematicsEngine(use_world_coords=True)

    frame_analyses = []
    for frame in pose_data.get("frames", []):
        # Format adapter for kinematics engine
        frame_dict = {
            "frame": frame.get("frame", 0),
            "time_seconds": frame.get("time_seconds", 0.0),
            "person_detected": frame.get("person_detected", False),
            "width": pose_data.get("width", 1920),
            "height": pose_data.get("height", 1080),
            "by_name": {lm["name"]: lm for lm in frame.get("landmarks", [])},
            "world_by_name": {},
        }
        res = engine.analyze_frame(frame_dict)
        frame_analyses.append(res)

    output = {
        "video": pose_data.get("video", "videos/test.mp4"),
        "fps": fps,
        "frame_count": len(frame_analyses),
        "frames": frame_analyses,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Processed {len(frame_analyses)} frames.")
    print(f"Kinematic results saved to: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
