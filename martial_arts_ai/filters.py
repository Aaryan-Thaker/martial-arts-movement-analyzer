"""
Temporal smoothing filters for keypoint coordinate streams.
Implements the One Euro Filter (Casiez et al., CHI 2012) to suppress
jitter at low speeds while eliminating lag during fast strikes.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple


class LowPassFilter:
    """First-order low-pass filter."""

    def __init__(self, alpha: float = 0.5) -> None:
        self.alpha = float(alpha)
        self.hat_x_prev: Optional[float] = None

    def reset(self) -> None:
        self.hat_x_prev = None

    def filter(self, x: float, alpha: Optional[float] = None) -> float:
        if alpha is not None:
            self.alpha = float(alpha)

        if self.hat_x_prev is None:
            hat_x = float(x)
        else:
            hat_x = self.alpha * float(x) + (1.0 - self.alpha) * self.hat_x_prev

        self.hat_x_prev = hat_x
        return hat_x


def _compute_alpha(rate: float, cutoff: float) -> float:
    """Compute smoothing factor alpha from sample rate (Hz) and cutoff frequency (Hz)."""
    if rate <= 0.0 or cutoff <= 0.0:
        return 1.0
    tau = 1.0 / (2.0 * math.pi * cutoff)
    te = 1.0 / rate
    return 1.0 / (1.0 + tau / te)


class OneEuroFilter:
    """
    1-Euro filter for 1D signals.
    Adapts cutoff frequency based on rate-of-change.
    """

    def __init__(
        self,
        freq: float = 30.0,
        min_cutoff: float = 1.0,
        beta: float = 0.05,
        d_cutoff: float = 1.0,
    ) -> None:
        """
        Args:
            freq: Estimate of sample rate in Hz.
            min_cutoff: Minimum cutoff frequency in Hz (smaller = smoother when static).
            beta: Speed coefficient (larger = less lag during rapid martial arts strikes).
            d_cutoff: Cutoff frequency for the derivative filter in Hz.
        """
        self.freq = float(freq)
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)

        self.x_filter = LowPassFilter()
        self.dx_filter = LowPassFilter()
        self.last_time: Optional[float] = None
        self.last_x: Optional[float] = None

    def reset(self) -> None:
        self.x_filter.reset()
        self.dx_filter.reset()
        self.last_time = None
        self.last_x = None

    def filter(self, x: float, timestamp: Optional[float] = None) -> float:
        """Filter value x given an optional timestamp in seconds."""
        if self.last_time is not None and timestamp is not None:
            dt = timestamp - self.last_time
            if dt > 0.0:
                self.freq = 1.0 / dt
        self.last_time = timestamp

        # Estimate derivative dx/dt
        if self.last_x is None:
            dx = 0.0
        else:
            dx = (x - self.last_x) * self.freq
        self.last_x = x

        # Filter the derivative
        alpha_d = _compute_alpha(self.freq, self.d_cutoff)
        edx = self.dx_filter.filter(dx, alpha=alpha_d)

        # Dynamic cutoff based on filtered derivative magnitude
        cutoff = self.min_cutoff + self.beta * abs(edx)
        alpha = _compute_alpha(self.freq, cutoff)

        return self.x_filter.filter(x, alpha=alpha)


class PointFilter3D:
    """Applies independent 1-Euro filters across 3D coordinates (x, y, z)."""

    def __init__(
        self,
        freq: float = 30.0,
        min_cutoff: float = 1.0,
        beta: float = 0.05,
        d_cutoff: float = 1.0,
    ) -> None:
        self.fx = OneEuroFilter(freq, min_cutoff, beta, d_cutoff)
        self.fy = OneEuroFilter(freq, min_cutoff, beta, d_cutoff)
        self.fz = OneEuroFilter(freq, min_cutoff, beta, d_cutoff)

    def reset(self) -> None:
        self.fx.reset()
        self.fy.reset()
        self.fz.reset()

    def filter(
        self,
        point: Tuple[float, float, float],
        timestamp: Optional[float] = None,
    ) -> Tuple[float, float, float]:
        x, y, z = point
        return (
            self.fx.filter(x, timestamp),
            self.fy.filter(y, timestamp),
            self.fz.filter(z, timestamp),
        )


class PoseFilterPool:
    """Pool of 3D filters for the full 33-landmark MediaPipe pose skeleton."""

    def __init__(
        self,
        landmark_count: int = 33,
        freq: float = 30.0,
        min_cutoff: float = 1.0,
        beta: float = 0.05,
        d_cutoff: float = 1.0,
    ) -> None:
        self.landmark_count = landmark_count
        self.filters: Dict[int, PointFilter3D] = {
            i: PointFilter3D(freq=freq, min_cutoff=min_cutoff, beta=beta, d_cutoff=d_cutoff)
            for i in range(landmark_count)
        }

    def reset(self) -> None:
        """Reset all landmark filters (e.g. after tracking drop or sequence change)."""
        for f in self.filters.values():
            f.reset()

    def filter_landmarks(
        self,
        landmarks: List[Dict[str, float]],
        timestamp: Optional[float] = None,
    ) -> List[Dict[str, float]]:
        """
        Filter a list of landmark dictionaries (each containing 'x', 'y', 'z', etc.).
        Returns smoothed copies preserving metadata.
        """
        smoothed: List[Dict[str, float]] = []
        for lm in landmarks:
            idx = int(lm.get("index", len(smoothed)))
            if idx in self.filters:
                orig = (float(lm.get("x", 0.0)), float(lm.get("y", 0.0)), float(lm.get("z", 0.0)))
                sx, sy, sz = self.filters[idx].filter(orig, timestamp)
                new_lm = dict(lm)
                new_lm["x"] = sx
                new_lm["y"] = sy
                new_lm["z"] = sz
                smoothed.append(new_lm)
            else:
                smoothed.append(dict(lm))
        return smoothed

