"""Unit tests for temporal smoothing filters."""

import math
import unittest
from martial_arts_ai.filters import LowPassFilter, OneEuroFilter, PointFilter3D, PoseFilterPool


class TestFilters(unittest.TestCase):
    def test_low_pass_filter_initialization(self):
        lpf = LowPassFilter(alpha=0.5)
        self.assertIsNone(lpf.hat_x_prev)
        self.assertEqual(lpf.filter(10.0), 10.0)
        self.assertEqual(lpf.filter(20.0), 15.0)  # 0.5 * 20 + 0.5 * 10

    def test_one_euro_filter_smoothing(self):
        f = OneEuroFilter(freq=30.0, min_cutoff=1.0, beta=0.0)
        val = 0.0
        for _ in range(10):
            val = f.filter(5.0)
        self.assertTrue(math.isclose(val, 5.0, abs_tol=0.01))

        step_val = f.filter(10.0)
        self.assertTrue(5.0 < step_val < 10.0)

    def test_point_filter_3d(self):
        pf = PointFilter3D(freq=30.0)
        filtered = pf.filter((1.0, 2.0, 3.0), timestamp=0.0)
        self.assertEqual(filtered, (1.0, 2.0, 3.0))

        filtered2 = pf.filter((1.1, 2.1, 3.1), timestamp=0.033)
        self.assertEqual(len(filtered2), 3)
        self.assertGreater(filtered2[0], 1.0)

    def test_pose_filter_pool_reset(self):
        pool = PoseFilterPool(landmark_count=33)
        lms = [{"index": 0, "x": 1.0, "y": 2.0, "z": 0.0}]
        smoothed = pool.filter_landmarks(lms, timestamp=0.0)
        self.assertEqual(smoothed[0]["x"], 1.0)
        pool.reset()
        self.assertIsNone(pool.filters[0].fx.x_filter.hat_x_prev)


if __name__ == "__main__":
    unittest.main()
