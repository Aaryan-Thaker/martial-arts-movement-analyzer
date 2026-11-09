"""
Biomechanical Kinematics Engine for Martial Arts Movement Analysis.
Fixes aspect-ratio distortion, computes rigorous 3D spatial joint angles,
angular velocities, guard integrity, kinetic chain hip rotation, and stance metrics.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

EPSILON = 1e-7


def _vector_3d(p1: Dict[str, float], p2: Dict[str, float], use_world: bool = False) -> np.ndarray:
    """Return 3D vector from p1 to p2."""
    if use_world and "x" in p1 and "y" in p1 and "z" in p1:
        return np.array([
            p2["x"] - p1["x"],
            p2["y"] - p1["y"],
            p2["z"] - p1["z"],
        ], dtype=np.float64)
    # Normalized / pixel space
    z1 = p1.get("z", 0.0)
    z2 = p2.get("z", 0.0)
    return np.array([
        p2["x"] - p1["x"],
        p2["y"] - p1["y"],
        z2 - z1,
    ], dtype=np.float64)


def calculate_3d_angle(
    a: Dict[str, float],
    b: Dict[str, float],
    c: Dict[str, float],
    use_world: bool = True,
) -> Optional[float]:
    """
    Calculate 3D interior spatial angle ABC at vertex B.
    Uses metric world coordinates if available to prevent planar projection errors.
    """
    ba = _vector_3d(b, a, use_world=use_world)
    bc = _vector_3d(b, c, use_world=use_world)

    mag_ba = float(np.linalg.norm(ba))
    mag_bc = float(np.linalg.norm(bc))

    if mag_ba < EPSILON or mag_bc < EPSILON:
        return None

    cosine = float(np.dot(ba, bc) / (mag_ba * mag_bc))
    cosine = max(-1.0, min(1.0, cosine))
    return float(math.degrees(math.acos(cosine)))


def calculate_2d_aspect_corrected_angle(
    a: Dict[str, float],
    b: Dict[str, float],
    c: Dict[str, float],
    width: float,
    height: float,
) -> Optional[float]:
    """
    Calculate 2D angle ABC scaled into isotropic pixel space.
    Eliminates aspect-ratio skew that occurs when calculating angles on [0, 1] normalized coordinates.
    """
    ba = np.array([(a["x"] - b["x"]) * width, (a["y"] - b["y"]) * height], dtype=np.float64)
    bc = np.array([(c["x"] - b["x"]) * width, (c["y"] - b["y"]) * height], dtype=np.float64)

    mag_ba = float(np.linalg.norm(ba))
    mag_bc = float(np.linalg.norm(bc))

    if mag_ba < EPSILON or mag_bc < EPSILON:
        return None

    cosine = float(np.dot(ba, bc) / (mag_ba * mag_bc))
    cosine = max(-1.0, min(1.0, cosine))
    return float(math.degrees(math.acos(cosine)))


class KinematicsEngine:
    """
    Stateful biomechanics analyzer tracking angles, velocities,
    guard status, and stance posture across video frames.
    """

    def __init__(self, use_world_coords: bool = True) -> None:
        self.use_world_coords = use_world_coords

        # State tracking for derivatives (velocities)
        self.prev_time: Optional[float] = None
        self.prev_angles: Dict[str, float] = {}
        self.prev_positions: Dict[str, np.ndarray] = {}
        self.tracking_was_lost: bool = True

    def reset(self) -> None:
        """Reset state tracking (e.g. after camera gap or video restart)."""
        self.prev_time = None
        self.prev_angles.clear()
        self.prev_positions.clear()
        self.tracking_was_lost = True

    def analyze_frame(self, frame_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze biomechanical metrics for a single frame.
        Handles tracking dropouts gracefully to eliminate false velocity spikes.
        """
        frame_idx = frame_data["frame"]
        time_seconds = frame_data["time_seconds"]
        person_detected = frame_data["person_detected"]

        analysis: Dict[str, Any] = {
            "frame": frame_idx,
            "time_seconds": time_seconds,
            "person_detected": person_detected,
            "angles": {},
            "angular_velocities": {},
            "limb_speeds": {},
            "torso": {},
            "guard": {},
            "stance": {},
            "movement": {
                "intensity": 0.0,
                "velocity_ms": 0.0,
            },
        }

        if not person_detected:
            # Person missing in this frame: reset tracker so future frames don't compute deltas across gaps
            self.reset()
            return analysis

        # Choose landmark source (prefer metric world landmarks when available)
        lms_2d = frame_data.get("by_name", {})
        lms_world = frame_data.get("world_by_name", {})
        w = float(frame_data.get("width", 1920))
        h = float(frame_data.get("height", 1080))

        use_world = self.use_world_coords and bool(lms_world)
        lms = lms_world if use_world else lms_2d

        # ------------------------------------------------------------------
        # 1. Spatial Joint Angles (Elbows, Knees, Shoulders, Hips)
        # ------------------------------------------------------------------
        angle_triplets = {
            "left_elbow": ("left_shoulder", "left_elbow", "left_wrist"),
            "right_elbow": ("right_shoulder", "right_elbow", "right_wrist"),
            "left_knee": ("left_hip", "left_knee", "left_ankle"),
            "right_knee": ("right_hip", "right_knee", "right_ankle"),
            "left_shoulder": ("left_hip", "left_shoulder", "left_elbow"),
            "right_shoulder": ("right_hip", "right_shoulder", "right_elbow"),
            "left_hip": ("left_shoulder", "left_hip", "left_knee"),
            "right_hip": ("right_shoulder", "right_hip", "right_knee"),
        }

        current_angles: Dict[str, float] = {}
        for angle_name, (a_name, b_name, c_name) in angle_triplets.items():
            if a_name in lms and b_name in lms and c_name in lms:
                if use_world:
                    angle = calculate_3d_angle(
                        lms[a_name], lms[b_name], lms[c_name], use_world=True
                    )
                else:
                    angle = calculate_2d_aspect_corrected_angle(
                        lms[a_name], lms[b_name], lms[c_name], width=w, height=h
                    )
                if angle is not None:
                    current_angles[angle_name] = round(angle, 2)

        analysis["angles"] = current_angles

        # ------------------------------------------------------------------
        # 2. Torso Twist & Hip Rotation (Power Generation / Kinetic Chain)
        # ------------------------------------------------------------------
        if all(k in lms for k in ["left_shoulder", "right_shoulder", "left_hip", "right_hip"]):
            ls, rs = lms["left_shoulder"], lms["right_shoulder"]
            lh, rh = lms["left_hip"], lms["right_hip"]

            # Shoulder and hip horizontal vectors in transverse plane (x, z)
            shoulder_vec = np.array([rs["x"] - ls["x"], rs.get("z", 0.0) - ls.get("z", 0.0)])
            hip_vec = np.array([rh["x"] - lh["x"], rh.get("z", 0.0) - lh.get("z", 0.0)])

            norm_s = float(np.linalg.norm(shoulder_vec))
            norm_h = float(np.linalg.norm(hip_vec))

            torso_twist_deg = 0.0
            if norm_s > EPSILON and norm_h > EPSILON:
                cos_rot = np.dot(shoulder_vec, hip_vec) / (norm_s * norm_h)
                cos_rot = max(-1.0, min(1.0, float(cos_rot)))
                torso_twist_deg = round(float(math.degrees(math.acos(cos_rot))), 2)

            analysis["torso"] = {
                "hip_shoulder_separation_deg": torso_twist_deg,
                "shoulder_width_metric": round(norm_s, 3) if use_world else None,
                "hip_width_metric": round(norm_h, 3) if use_world else None,
            }

        # ------------------------------------------------------------------
        # 3. Guard Integrity & Stance Geometry
        # ------------------------------------------------------------------
        if "nose" in lms_2d and "left_wrist" in lms_2d and "right_wrist" in lms_2d:
            nose = lms_2d["nose"]
            lw = lms_2d["left_wrist"]
            rw = lms_2d["right_wrist"]
            ls = lms_2d.get("left_shoulder", {"y": nose["y"] + 0.15})
            rs = lms_2d.get("right_shoulder", {"y": nose["y"] + 0.15})
            shoulder_y = (ls["y"] + rs["y"]) / 2.0

            # Guard is considered "HIGH" if at least one hand is at/above shoulder level
            left_hand_up = lw["y"] <= shoulder_y + 0.05
            right_hand_up = rw["y"] <= shoulder_y + 0.05

            guard_status = "DROPPED"
            if left_hand_up and right_hand_up:
                guard_status = "GUARD_HIGH"
            elif left_hand_up or right_hand_up:
                guard_status = "GUARD_MID"

            analysis["guard"] = {
                "status": guard_status,
                "left_wrist_rel_y": round(lw["y"] - nose["y"], 3),
                "right_wrist_rel_y": round(rw["y"] - nose["y"], 3),
            }

        # Stance classification candidate
        if all(k in lms_2d for k in ["left_ankle", "right_ankle", "left_knee", "right_knee"]):
            la, ra = lms_2d["left_ankle"], lms_2d["right_ankle"]
            lk_ang = current_angles.get("left_knee", 180.0)
            rk_ang = current_angles.get("right_knee", 180.0)

            dx = abs(la["x"] - ra["x"])
            dy = abs(la["y"] - ra["y"])
            stance_width = math.sqrt(dx * dx + dy * dy)

            stance_type = "SHIZENTAI"  # Natural
            if stance_width > 0.25:
                # Deep/wide stance
                if lk_ang < 135.0 or rk_ang < 135.0:
                    stance_type = "ZENKUTSU_DACHI"  # Front stance
                else:
                    stance_type = "KIBA_DACHI"  # Horse stance

            analysis["stance"] = {
                "detected_type": stance_type,
                "feet_separation": round(stance_width, 3),
                "left_knee_flexion": lk_ang,
                "right_knee_flexion": rk_ang,
            }

        # ------------------------------------------------------------------
        # 4. Velocities & Movement Intensity (With Tracking Recovery Protection)
        # ------------------------------------------------------------------
        current_positions: Dict[str, np.ndarray] = {}
        tracked_joints = [
            "left_wrist", "right_wrist",
            "left_ankle", "right_ankle",
            "left_elbow", "right_elbow",
            "left_knee", "right_knee",
        ]

        for name in tracked_joints:
            if name in lms:
                pos = lms[name]
                current_positions[name] = np.array([
                    pos["x"], pos["y"], pos.get("z", 0.0)
                ], dtype=np.float64)

        if not self.tracking_was_lost and self.prev_time is not None:
            dt = time_seconds - self.prev_time
            if dt > 0.001:
                # Angular velocities (deg/s)
                angular_vels: Dict[str, float] = {}
                for k, ang in current_angles.items():
                    if k in self.prev_angles:
                        vel = (ang - self.prev_angles[k]) / dt
                        angular_vels[k] = round(float(vel), 2)
                analysis["angular_velocities"] = angular_vels

                # Joint linear speeds
                joint_speeds: List[float] = []
                limb_speeds: Dict[str, float] = {}
                for name, pos in current_positions.items():
                    if name in self.prev_positions:
                        dist = float(np.linalg.norm(pos - self.prev_positions[name]))
                        speed = dist / dt
                        limb_speeds[name] = round(speed, 3)
                        joint_speeds.append(speed)

                analysis["limb_speeds"] = limb_speeds
                if joint_speeds:
                    mean_speed = sum(joint_speeds) / len(joint_speeds)
                    analysis["movement"]["intensity"] = round(mean_speed, 4)
                    analysis["movement"]["velocity_ms"] = round(mean_speed, 3) if use_world else None

        # Update historical state for the next frame
        self.prev_time = time_seconds
        self.prev_angles = current_angles
        self.prev_positions = current_positions
        self.tracking_was_lost = False

        return analysis

