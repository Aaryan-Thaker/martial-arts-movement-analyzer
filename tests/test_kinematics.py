"""Unit tests for 3D kinematics, aspect ratio correction, and engine."""

import math
import unittest
from martial_arts_ai.kinematics import (
    calculate_3d_angle,
    calculate_2d_aspect_corrected_angle,
    KinematicsEngine,
)


class TestKinematics(unittest.TestCase):
    def test_3d_right_angle(self):
        # 90-degree right angle in 3D: (1, 0, 0) -> (0, 0, 0) -> (0, 1, 0)
        a = {"x": 1.0, "y": 0.0, "z": 0.0}
        b = {"x": 0.0, "y": 0.0, "z": 0.0}
        c = {"x": 0.0, "y": 1.0, "z": 0.0}

        angle = calculate_3d_angle(a, b, c, use_world=True)
        self.assertIsNotNone(angle)
        self.assertTrue(math.isclose(angle, 90.0, abs_tol=0.01))

    def test_3d_straight_line(self):
        # 180-degree angle: (-1, 0, 0) -> (0, 0, 0) -> (1, 0, 0)
        a = {"x": -1.0, "y": 0.0, "z": 0.0}
        b = {"x": 0.0, "y": 0.0, "z": 0.0}
        c = {"x": 1.0, "y": 0.0, "z": 0.0}

        angle = calculate_3d_angle(a, b, c, use_world=True)
        self.assertIsNotNone(angle)
        self.assertTrue(math.isclose(angle, 180.0, abs_tol=0.01))

    def test_aspect_ratio_correction(self):
        # In normalized coordinates on a 1920x1080 display:
        a = {"x": 0.1, "y": 0.0}
        b = {"x": 0.0, "y": 0.0}
        c = {"x": 0.1, "y": 0.1}

        ang_corrected = calculate_2d_aspect_corrected_angle(a, b, c, width=1920, height=1080)
        self.assertIsNotNone(ang_corrected)
        expected = math.degrees(math.atan2(108, 192))
        self.assertTrue(math.isclose(ang_corrected, expected, abs_tol=0.1))

    def test_engine_dropout_protection(self):
        engine = KinematicsEngine()

        frame1 = {
            "frame": 0,
            "time_seconds": 0.0,
            "person_detected": True,
            "width": 1920,
            "height": 1080,
            "by_name": {
                "left_shoulder": {"x": 0.4, "y": 0.3},
                "left_elbow": {"x": 0.4, "y": 0.5},
                "left_wrist": {"x": 0.4, "y": 0.7},
            },
            "world_by_name": {},
        }
        res1 = engine.analyze_frame(frame1)
        self.assertIn("left_elbow", res1["angles"])

        # Frame 2: person lost
        frame2 = {
            "frame": 1,
            "time_seconds": 1.0,
            "person_detected": False,
            "width": 1920,
            "height": 1080,
        }
        res2 = engine.analyze_frame(frame2)
        self.assertFalse(res2["person_detected"])

        # Frame 3: person re-enters 5 seconds later at a different position
        frame3 = {
            "frame": 2,
            "time_seconds": 6.0,
            "person_detected": True,
            "width": 1920,
            "height": 1080,
            "by_name": {
                "left_shoulder": {"x": 0.8, "y": 0.3},
                "left_elbow": {"x": 0.8, "y": 0.5},
                "left_wrist": {"x": 0.8, "y": 0.7},
            },
            "world_by_name": {},
        }
        res3 = engine.analyze_frame(frame3)
        # Intensity and velocity MUST be 0.0 (no false spike across dropout)
        self.assertEqual(res3["movement"]["intensity"], 0.0)
        self.assertEqual(len(res3["angular_velocities"]), 0)


if __name__ == "__main__":
    unittest.main()
