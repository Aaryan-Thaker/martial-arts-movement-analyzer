"""
Visual telemetry overlay and video rendering for martial arts analysis.
Renders joint angle arcs, speed gauges, guard badges, stance HUD,
and encodes videos using browser-compatible H.264 (avc1) with mp4v fallback.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from martial_arts_ai.detector import POSE_CONNECTIONS

# Martial arts color palette (BGR format for OpenCV)
COLOR_TORSO = (245, 180, 50)       # Cyan-gold
COLOR_ARMS = (0, 220, 255)         # Bright amber / gold
COLOR_LEGS = (255, 120, 0)         # Deep blue / azure
COLOR_JOINTS = (255, 255, 255)     # Clean white
COLOR_TEXT = (255, 255, 255)       # White
COLOR_HUD_BG = (20, 20, 20)        # Dark translucent overlay
COLOR_SUCCESS = (80, 220, 100)     # Emerald green
COLOR_WARNING = (0, 165, 255)      # Orange
COLOR_ALERT = (50, 50, 240)        # Crimson red


class OverlayRenderer:
    """Renders biomechanical telemetry directly onto OpenCV frames."""

    def __init__(
        self,
        show_skeleton: bool = True,
        show_angles: bool = True,
        show_hud: bool = True,
        show_guard: bool = True,
        show_velocity_bar: bool = True,
    ) -> None:
        self.show_skeleton = show_skeleton
        self.show_angles = show_angles
        self.show_hud = show_hud
        self.show_guard = show_guard
        self.show_velocity_bar = show_velocity_bar

    def render_frame(
        self,
        frame_bgr: np.ndarray,
        pose_data: Dict[str, Any],
        kinematics: Dict[str, Any],
        technique_label: Optional[str] = None,
    ) -> np.ndarray:
        """
        Draw telemetry overlay onto a copy of the frame.

        Args:
            frame_bgr: Source OpenCV BGR image matrix.
            pose_data: Output of PoseDetector.detect_frame.
            kinematics: Output of KinematicsEngine.analyze_frame.
            technique_label: Optional name of the currently active movement/kata technique.

        Returns:
            Annotated BGR image matrix.
        """
        canvas = frame_bgr.copy()
        h, w = canvas.shape[:2]

        if not pose_data.get("person_detected", False):
            # Render subtle search/lost badge
            cv2.putText(
                canvas,
                "POSE: SEARCHING...",
                (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                COLOR_WARNING,
                2,
                cv2.LINE_AA,
            )
            return canvas

        landmarks = pose_data.get("landmarks", [])
        lms_by_name = pose_data.get("by_name", {})
        angles = kinematics.get("angles", {})
        guard = kinematics.get("guard", {})
        stance = kinematics.get("stance", {})
        intensity = kinematics.get("movement", {}).get("intensity", 0.0)

        # ------------------------------------------------------------------
        # 1. Draw Skeleton Connections & Joint Circles
        # ------------------------------------------------------------------
        if self.show_skeleton and landmarks:
            # Bones
            for a_idx, b_idx in POSE_CONNECTIONS:
                if a_idx >= len(landmarks) or b_idx >= len(landmarks):
                    continue
                pa = landmarks[a_idx]
                pb = landmarks[b_idx]

                # Determine limb category for coloring
                if a_idx in (11, 12, 23, 24) and b_idx in (11, 12, 23, 24):
                    line_color = COLOR_TORSO
                elif a_idx in (11, 13, 15, 12, 14, 16) or b_idx in (11, 13, 15, 12, 14, 16):
                    line_color = COLOR_ARMS
                else:
                    line_color = COLOR_LEGS

                pt1 = (int(pa["pixel_x"]), int(pa["pixel_y"]))
                pt2 = (int(pb["pixel_x"]), int(pb["pixel_y"]))

                if 0 <= pt1[0] < w and 0 <= pt1[1] < h and 0 <= pt2[0] < w and 0 <= pt2[1] < h:
                    cv2.line(canvas, pt1, pt2, line_color, 2, cv2.LINE_AA)

            # Joints
            for lm in landmarks:
                x = int(lm["pixel_x"])
                y = int(lm["pixel_y"])
                if 0 <= x < w and 0 <= y < h:
                    cv2.circle(canvas, (x, y), 4, COLOR_JOINTS, -1, cv2.LINE_AA)

        # ------------------------------------------------------------------
        # 2. Draw Key Joint Angle Telemetry
        # ------------------------------------------------------------------
        if self.show_angles:
            angle_targets = [
                ("left_elbow", "left_elbow"),
                ("right_elbow", "right_elbow"),
                ("left_knee", "left_knee"),
                ("right_knee", "right_knee"),
            ]
            for angle_key, lm_name in angle_targets:
                if angle_key in angles and lm_name in lms_by_name:
                    deg = angles[angle_key]
                    pt = lms_by_name[lm_name]
                    px, py = int(pt["pixel_x"]), int(pt["pixel_y"])

                    # Draw text with subtle shadow
                    txt = f"{int(deg)}deg"
                    cv2.putText(
                        canvas, txt, (px + 10, py - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 0, 0), 3, cv2.LINE_AA
                    )
                    cv2.putText(
                        canvas, txt, (px + 10, py - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, COLOR_ARMS if "elbow" in angle_key else COLOR_LEGS,
                        1, cv2.LINE_AA
                    )

        # ------------------------------------------------------------------
        # 3. HUD Overlay (Top & Bottom Dashboards)
        # ------------------------------------------------------------------
        if self.show_hud:
            # Top-left HUD Card
            hud_w, hud_h = 320, 115
            sub = canvas[15:15 + hud_h, 20:20 + hud_w]
            black_rect = np.zeros_like(sub)
            cv2.addWeighted(sub, 0.35, black_rect, 0.65, 0, sub)
            canvas[15:15 + hud_h, 20:20 + hud_w] = sub
            cv2.rectangle(canvas, (20, 15), (20 + hud_w, 15 + hud_h), (80, 80, 80), 1)

            # Title
            cv2.putText(
                canvas, "MARTIAL ARTS AI", (32, 38),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA
            )

            # Guard Status
            guard_status = guard.get("status", "DROPPED")
            guard_color = COLOR_SUCCESS if guard_status == "GUARD_HIGH" else (
                COLOR_WARNING if guard_status == "GUARD_MID" else COLOR_ALERT
            )
            cv2.putText(
                canvas, f"GUARD: {guard_status}", (32, 62),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, guard_color, 1, cv2.LINE_AA
            )

            # Stance
            stance_type = stance.get("detected_type", "SHIZENTAI")
            cv2.putText(
                canvas, f"STANCE: {stance_type}", (32, 84),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA
            )

            # Technique / Timestamp
            time_sec = kinematics.get("time_seconds", 0.0)
            tech_txt = technique_label if technique_label else f"T: {time_sec:.2f}s"
            cv2.putText(
                canvas, tech_txt, (32, 106),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 220, 255), 1, cv2.LINE_AA
            )

        # ------------------------------------------------------------------
        # 4. Movement Intensity / Velocity Gauge (Bottom)
        # ------------------------------------------------------------------
        if self.show_velocity_bar:
            bar_x = 20
            bar_y = h - 25
            bar_max_w = min(400, w - 40)
            bar_h = 10

            # Background bar
            cv2.rectangle(canvas, (bar_x, bar_y), (bar_x + bar_max_w, bar_y + bar_h), (40, 40, 40), -1)

            # Normalized velocity width (clipped at max 1.0)
            ratio = min(1.0, float(intensity) / 1.5)
            filled_w = int(bar_max_w * ratio)

            # Color transitions from green to red based on intensity
            gauge_color = (
                int(255 * ratio),
                int(255 * (1.0 - ratio)),
                80
            )
            if filled_w > 0:
                cv2.rectangle(canvas, (bar_x, bar_y), (bar_x + filled_w, bar_y + bar_h), gauge_color, -1)

            cv2.putText(
                canvas, f"SPEED: {intensity:.2f}", (bar_x, bar_y - 6),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1, cv2.LINE_AA
            )

        return canvas


def create_video_writer(
    output_path: str | Path,
    fps: float,
    width: int,
    height: int,
) -> Tuple[cv2.VideoWriter, str]:
    """
    Create an OpenCV VideoWriter configured with browser-compatible H.264 (avc1),
    falling back gracefully to mp4v if avc1 is not supported by the local FFmpeg build.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Attempt 1: H.264 / avc1 (standard for web / HTML5 video playback)
    codec = "avc1"
    fourcc = cv2.VideoWriter_fourcc(*codec)
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    if not writer.isOpened():
        # Attempt 2: mp4v fallback
        codec = "mp4v"
        fourcc = cv2.VideoWriter_fourcc(*codec)
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    if not writer.isOpened():
        raise RuntimeError(f"Could not open VideoWriter for {output_path} with avc1 or mp4v.")

    return writer, codec

