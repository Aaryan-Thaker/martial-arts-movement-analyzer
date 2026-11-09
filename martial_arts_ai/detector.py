"""
MediaPipe Pose Tasks detection wrapper.
Supports video files, live camera streams, metric world landmarks,
and integrated OneEuroFilter temporal smoothing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np

from martial_arts_ai.filters import PoseFilterPool

# Official 33 MediaPipe pose landmark names
LANDMARK_NAMES: List[str] = [
    "nose",
    "left_eye_inner",
    "left_eye",
    "left_eye_outer",
    "right_eye_inner",
    "right_eye",
    "right_eye_outer",
    "left_ear",
    "right_ear",
    "mouth_left",
    "mouth_right",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_pinky",
    "right_pinky",
    "left_index",
    "right_index",
    "left_thumb",
    "right_thumb",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
]

POSE_CONNECTIONS: List[Tuple[int, int]] = [
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    (11, 12),
    (11, 13), (13, 15),
    (12, 14), (14, 16),
    (11, 23), (12, 24),
    (23, 24),
    (23, 25), (25, 27),
    (24, 26), (26, 28),
    (27, 29), (29, 31),
    (28, 30), (30, 32),
]


class PoseDetector:
    """High-level wrapper for MediaPipe Pose Landmarker Tasks API."""

    def __init__(
        self,
        model_path: str | Path = "models/pose_landmarker_full.task",
        min_detection_confidence: float = 0.5,
        min_presence_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        enable_smoothing: bool = True,
        filter_freq: float = 30.0,
        filter_min_cutoff: float = 1.0,
        filter_beta: float = 0.05,
    ) -> None:
        self.model_path = Path(model_path)
        self._ensure_model_exists()

        self.min_detection_confidence = min_detection_confidence
        self.min_presence_confidence = min_presence_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.enable_smoothing = enable_smoothing

        self.filter_pool: Optional[PoseFilterPool] = None
        self.world_filter_pool: Optional[PoseFilterPool] = None
        if enable_smoothing:
            self.filter_pool = PoseFilterPool(
                freq=filter_freq,
                min_cutoff=filter_min_cutoff,
                beta=filter_beta,
            )
            self.world_filter_pool = PoseFilterPool(
                freq=filter_freq,
                min_cutoff=filter_min_cutoff,
                beta=filter_beta,
            )

        self.landmarker: Optional[mp.tasks.vision.PoseLandmarker] = None
        self._initialize_landmarker()

    def _ensure_model_exists(self) -> None:
        if not self.model_path.exists() or self.model_path.stat().st_size == 0:
            try:
                from download_model import download_model
                print(f"[PoseDetector] Model not found at {self.model_path}. Auto-downloading...")
                download_model(dest=self.model_path)
            except Exception as exc:
                raise FileNotFoundError(
                    f"Pose model asset not found at {self.model_path} and auto-download failed: {exc}"
                ) from exc

    def _initialize_landmarker(self) -> None:
        base_options = mp.tasks.BaseOptions(
            model_asset_path=str(self.model_path.resolve())
        )
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=self.min_detection_confidence,
            min_pose_presence_confidence=self.min_presence_confidence,
            min_tracking_confidence=self.min_tracking_confidence,
            output_segmentation_masks=False,
        )
        self.landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)

    def reset_tracking(self) -> None:
        """Reset temporal filter states after video seek, tracking drop, or scene cut."""
        if self.filter_pool:
            self.filter_pool.reset()
        if self.world_filter_pool:
            self.world_filter_pool.reset()

    def detect_frame(
        self,
        frame_bgr: np.ndarray,
        timestamp_ms: int,
        frame_number: int = 0,
    ) -> Dict[str, Any]:
        """
        Process a single BGR video frame and extract pose landmarks.

        Args:
            frame_bgr: OpenCV BGR image matrix.
            timestamp_ms: Monotonically increasing timestamp in milliseconds.
            frame_number: Optional sequential frame index.

        Returns:
            Structured dictionary with normalized landmarks, world landmarks,
            and fast name-keyed dictionaries.
        """
        if self.landmarker is None:
            raise RuntimeError("PoseDetector is not initialized or has been closed.")

        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        result = self.landmarker.detect_for_video(mp_image, int(timestamp_ms))

        time_seconds = float(timestamp_ms) / 1000.0
        frame_data: Dict[str, Any] = {
            "frame": frame_number,
            "timestamp_ms": timestamp_ms,
            "time_seconds": time_seconds,
            "person_detected": False,
            "width": w,
            "height": h,
            "landmarks": [],
            "world_landmarks": [],
            "by_name": {},
            "world_by_name": {},
        }

        if not result.pose_landmarks:
            # Person not detected; reset filter state to prevent interpolation spikes across gaps
            self.reset_tracking()
            return frame_data

        frame_data["person_detected"] = True
        raw_lms = result.pose_landmarks[0]
        raw_world_lms = (
            result.pose_world_landmarks[0] if result.pose_world_landmarks else None
        )

        landmarks: List[Dict[str, Any]] = []
        for idx, lm in enumerate(raw_lms):
            landmarks.append({
                "index": idx,
                "name": LANDMARK_NAMES[idx] if idx < len(LANDMARK_NAMES) else f"pt_{idx}",
                "x": float(lm.x),
                "y": float(lm.y),
                "z": float(lm.z),
                "pixel_x": float(lm.x * w),
                "pixel_y": float(lm.y * h),
                "visibility": float(getattr(lm, "visibility", 1.0)),
                "presence": float(getattr(lm, "presence", 1.0)),
            })

        world_landmarks: List[Dict[str, Any]] = []
        if raw_world_lms:
            for idx, wlm in enumerate(raw_world_lms):
                world_landmarks.append({
                    "index": idx,
                    "name": LANDMARK_NAMES[idx] if idx < len(LANDMARK_NAMES) else f"pt_{idx}",
                    "x": float(wlm.x),  # metric meters
                    "y": float(wlm.y),
                    "z": float(wlm.z),
                    "visibility": float(getattr(wlm, "visibility", 1.0)),
                    "presence": float(getattr(wlm, "presence", 1.0)),
                })

        # Apply OneEuroFilter temporal smoothing
        if self.enable_smoothing and self.filter_pool:
            landmarks = self.filter_pool.filter_landmarks(landmarks, timestamp=time_seconds)
            # Recompute pixel coordinates from smoothed normalized coordinates
            for lm in landmarks:
                lm["pixel_x"] = lm["x"] * w
                lm["pixel_y"] = lm["y"] * h

        if self.enable_smoothing and self.world_filter_pool and world_landmarks:
            world_landmarks = self.world_filter_pool.filter_landmarks(
                world_landmarks, timestamp=time_seconds
            )

        frame_data["landmarks"] = landmarks
        frame_data["world_landmarks"] = world_landmarks
        frame_data["by_name"] = {lm["name"]: lm for lm in landmarks}
        frame_data["world_by_name"] = {wlm["name"]: wlm for wlm in world_landmarks}

        return frame_data

    def close(self) -> None:
        if self.landmarker is not None:
            self.landmarker.close()
            self.landmarker = None

    def __enter__(self) -> "PoseDetector":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

