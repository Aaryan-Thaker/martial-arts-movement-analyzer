#!/usr/bin/env python3
"""
Legacy wrapper for pose extraction.
Powered by the modular martial_arts_ai package.
"""

from pathlib import Path
from martial_arts_ai.cli import main
import sys

if __name__ == "__main__":
    sys.argv = [
        "martial-arts-ai",
        "analyze",
        "--input", "videos/test.mp4",
        "--output", "videos/pose_output.mp4",
        "--json-out", "videos/movement_analysis.json",
        "--segments-out", "videos/movement_segments.json",
    ]
    main()
