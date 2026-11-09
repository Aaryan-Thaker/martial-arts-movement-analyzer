"""
Martial Arts AI - Computer Vision & Biomechanical Movement Analyzer.
"""

from martial_arts_ai.detector import PoseDetector, POSE_CONNECTIONS, LANDMARK_NAMES
from martial_arts_ai.filters import OneEuroFilter, PointFilter3D, PoseFilterPool
from martial_arts_ai.kinematics import KinematicsEngine, calculate_3d_angle, calculate_2d_aspect_corrected_angle
from martial_arts_ai.segmenter import MovementSegmenter
from martial_arts_ai.visualizer import OverlayRenderer, create_video_writer

__version__ = "0.1.0"
__all__ = [
    "PoseDetector",
    "POSE_CONNECTIONS",
    "LANDMARK_NAMES",
    "OneEuroFilter",
    "PointFilter3D",
    "PoseFilterPool",
    "KinematicsEngine",
    "calculate_3d_angle",
    "calculate_2d_aspect_corrected_angle",
    "MovementSegmenter",
    "OverlayRenderer",
    "create_video_writer",
]

