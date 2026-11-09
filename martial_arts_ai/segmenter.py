"""
Movement segmentation engine for martial arts techniques and katas.
Uses adaptive kinematic velocity profiles, prominence peak detection,
and valley / stance-hold zero-crossing detection to partition continuous sequences.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.signal import find_peaks


class MovementSegmenter:
    """
    Analyzes kinematic movement intensity signals to automatically partition
    strikes, blocks, and transitions into discrete movement segments.
    """

    def __init__(
        self,
        smoothing_window: int = 15,
        min_peak_distance_seconds: float = 0.75,
        peak_prominence: float = 0.05,
        hold_threshold_ratio: float = 0.20,
    ) -> None:
        """
        Args:
            smoothing_window: Moving average window size (frames).
            min_peak_distance_seconds: Minimum temporal separation between candidate techniques.
            peak_prominence: Relative prominence threshold for SciPy find_peaks.
            hold_threshold_ratio: Intensity fraction considered stationary/stance hold.
        """
        self.smoothing_window = smoothing_window
        self.min_peak_distance_seconds = min_peak_distance_seconds
        self.peak_prominence = peak_prominence
        self.hold_threshold_ratio = hold_threshold_ratio

    def segment_analysis(
        self,
        frames_analysis: List[Dict[str, Any]],
        fps: float = 30.0,
    ) -> Dict[str, Any]:
        """
        Segment a sequence of frame analysis dictionaries into discrete movements.

        Args:
            frames_analysis: List of dicts produced by KinematicsEngine.analyze_frame.
            fps: Frame rate of the video sequence.

        Returns:
            Dictionary with candidate segments, peak metadata, and summary stats.
        """
        if not frames_analysis:
            return {"segments": [], "peaks_count": 0, "fps": fps}

        valid_frames = [
            f for f in frames_analysis if f.get("person_detected", False)
        ]

        if len(valid_frames) < self.smoothing_window:
            return {"segments": [], "peaks_count": 0, "fps": fps}

        times = np.array([float(f["time_seconds"]) for f in valid_frames], dtype=np.float64)
        intensities = np.array(
            [float(f.get("movement", {}).get("intensity", 0.0)) for f in valid_frames],
            dtype=np.float64,
        )

        # ------------------------------------------------------------------
        # 1. Smooth intensity signal
        # ------------------------------------------------------------------
        win = max(3, self.smoothing_window)
        if win % 2 == 0:
            win += 1
        kernel = np.ones(win, dtype=np.float64) / win
        smoothed = np.convolve(intensities, kernel, mode="same")

        # ------------------------------------------------------------------
        # 2. Detect kinematic peaks
        # ------------------------------------------------------------------
        min_distance = max(1, int(self.min_peak_distance_seconds * fps))
        # Scale prominence dynamically based on signal amplitude
        sig_range = float(np.ptp(smoothed)) if len(smoothed) > 0 else 1.0
        adaptive_prominence = max(0.001, self.peak_prominence * sig_range)

        peak_indices, properties = find_peaks(
            smoothed,
            distance=min_distance,
            prominence=adaptive_prominence,
        )

        # ------------------------------------------------------------------
        # 3. Dynamic valley & hold boundary detection
        # ------------------------------------------------------------------
        segments: List[Dict[str, Any]] = []

        for i, peak_idx in enumerate(peak_indices):
            peak_time = float(times[peak_idx])
            peak_intensity = float(smoothed[peak_idx])

            # Determine start boundary by looking backward to the previous valley
            if i == 0:
                left_bound = 0
            else:
                left_bound = peak_indices[i - 1]

            # Find the minimum intensity point (velocity valley) between previous peak and current peak
            if peak_idx > left_bound:
                valley_left = left_bound + int(np.argmin(smoothed[left_bound:peak_idx]))
                start_time = float(times[valley_left])
            else:
                start_time = float(times[0])

            # Determine end boundary by looking forward to the next valley
            if i == len(peak_indices) - 1:
                right_bound = len(smoothed) - 1
            else:
                right_bound = peak_indices[i + 1]

            if right_bound > peak_idx:
                valley_right = peak_idx + int(np.argmin(smoothed[peak_idx:right_bound]))
                end_time = float(times[valley_right])
            else:
                end_time = float(times[-1])

            duration = max(0.1, end_time - start_time)

            # Detect stance hold / stabilization:
            # Measure how long intensity stays near the valley threshold before the next movement
            valley_intensity = float(smoothed[valley_right]) if right_bound > peak_idx else 0.0
            is_hold_detected = valley_intensity < (peak_intensity * self.hold_threshold_ratio)

            # Determine dominant limb at peak
            peak_frame = valid_frames[peak_idx]
            dominant_limb = self._detect_dominant_limb(peak_frame)

            segment_dict: Dict[str, Any] = {
                "id": i + 1,
                "name": f"Technique {i + 1}",
                "start": round(start_time, 2),
                "peak": round(peak_time, 2),
                "end": round(end_time, 2),
                "duration": round(duration, 2),
                "peak_intensity": round(peak_intensity, 4),
                "dominant_limb": dominant_limb,
                "stance_hold": is_hold_detected,
                "detected_stance": peak_frame.get("stance", {}).get("detected_type", "UNKNOWN"),
                "guard_status": peak_frame.get("guard", {}).get("status", "UNKNOWN"),
            }
            segments.append(segment_dict)

        return {
            "fps": fps,
            "total_frames_analyzed": len(valid_frames),
            "peaks_count": len(peak_indices),
            "segments": segments,
            "average_technique_duration": round(
                float(np.mean([s["duration"] for s in segments])) if segments else 0.0, 2
            ),
        }

    @staticmethod
    def _detect_dominant_limb(frame: Dict[str, Any]) -> str:
        """Infer which limb had highest speed in the peak frame."""
        speeds = frame.get("limb_speeds", {})
        if not speeds:
            return "body"
        max_limb = max(speeds.items(), key=lambda kv: kv[1])[0]
        return max_limb.replace("_", " ").title()

