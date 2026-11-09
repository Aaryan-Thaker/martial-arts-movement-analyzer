#!/usr/bin/env python3
"""
Movement intensity plot utility.
Reads movement_analysis.json and plots or saves kinematic speed over time.
"""

import json
from pathlib import Path
import matplotlib.pyplot as plt

INPUT_JSON = Path("videos/movement_analysis.json")
OUTPUT_PLOT = Path("videos/movement_plot.png")


def main() -> None:
    if not INPUT_JSON.exists():
        print(f"[Error] {INPUT_JSON} not found. Run analysis first.")
        return

    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    times = []
    intensities = []

    for frame in data.get("frames", []):
        if frame.get("person_detected", False):
            times.append(frame.get("time_seconds", 0.0))
            intensities.append(
                frame.get("movement", {}).get("intensity", 0.0)
            )

    if not times:
        print("[Notice] No detected frames to plot.")
        return

    plt.figure(figsize=(12, 5))
    plt.plot(times, intensities, color="#00bcd4", label="Limb Velocity / Intensity")
    plt.xlabel("Time (seconds)")
    plt.ylabel("Movement Intensity")
    plt.title("Martial Arts Movement Intensity Profile")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend()
    plt.tight_layout()

    OUTPUT_PLOT.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_PLOT, dpi=150)
    print(f"[Plot] Saved graph to {OUTPUT_PLOT}")

    try:
        # Show interactive window if supported
        plt.show()
    except Exception:
        pass


if __name__ == "__main__":
    main()
