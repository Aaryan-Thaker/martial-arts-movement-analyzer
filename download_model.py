#!/usr/bin/env python3
"""
Model download script for MediaPipe Pose Landmarker Task.
Downloads the float16 full model asset if it is not already present locally.
"""

import sys
import urllib.request
from pathlib import Path

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_full/float16/latest/pose_landmarker_full.task"
)
DEST_PATH = Path("models/pose_landmarker_full.task")


def download_model(dest: Path = DEST_PATH, url: str = MODEL_URL, force: bool = False) -> Path:
    dest = Path(dest)
    if dest.exists() and dest.stat().st_size > 0 and not force:
        print(f"[download_model] Model already exists at: {dest.resolve()} ({dest.stat().st_size / 1024 / 1024:.2f} MB)")
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"[download_model] Downloading MediaPipe Pose model from:\n  {url}")
    print(f"[download_model] Target location: {dest.resolve()}")

    def _progress_hook(block_num: int, block_size: int, total_size: int) -> None:
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(100.0, downloaded * 100.0 / total_size)
            sys.stdout.write(f"\r[download_model] Progress: {percent:.1f}% ({downloaded / 1024 / 1024:.2f} MB / {total_size / 1024 / 1024:.2f} MB)")
            sys.stdout.flush()

    try:
        urllib.request.urlretrieve(url, dest, reporthook=_progress_hook)
        print("\n[download_model] Download completed successfully.")
    except Exception as exc:
        if dest.exists():
            dest.unlink(missing_ok=True)
        raise RuntimeError(f"Failed to download model asset from {url}: {exc}") from exc

    return dest


if __name__ == "__main__":
    download_model()

