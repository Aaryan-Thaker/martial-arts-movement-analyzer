#!/usr/bin/env python3
"""
Legacy wrapper for movement segmentation.
Uses martial_arts_ai.MovementSegmenter with adaptive velocity signals
and stance-hold detection.
"""

import json
from pathlib import Path
from martial_arts_ai.segmenter import MovementSegmenter

INPUT_JSON = Path("videos/movement_analysis.json")
OUTPUT_JSON = Path("videos/movement_segments.json")


def main() -> None:
    print("=" * 60)
    print(" Candidate Movement Detection (Modular Segmenter)")
    print("=" * 60)

    if not INPUT_JSON.exists():
        print(f"[Notice] {INPUT_JSON} not found. Running full analysis pipeline first...")
        from martial_arts_ai.cli import main as cli_main
        import sys
        sys.argv = ["martial-arts-ai", "analyze"]
        cli_main()
        return

    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    fps = data.get("fps", 30.0)
    frames = data.get("frames", [])

    segmenter = MovementSegmenter()
    result = segmenter.segment_analysis(frames, fps=fps)

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    for seg in result.get("segments", []):
        print(
            f"{seg['name']}: {seg['start']:.2f}s -> {seg['end']:.2f}s "
            f"(peak {seg['peak']:.2f}s | dominant: {seg['dominant_limb']} | stance: {seg['detected_stance']})"
        )

    print()
    print(f"Detected {result['peaks_count']} candidate movements.")
    print(f"Saved to: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
