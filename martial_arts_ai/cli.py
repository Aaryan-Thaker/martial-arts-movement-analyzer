"""
Unified CLI for the Martial Arts Movement Analyzer.
Supports offline video analysis, real-time live webcam processing,
movement segmentation, and direct export to the Next.js frontend.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2

from martial_arts_ai.detector import PoseDetector
from martial_arts_ai.kinematics import KinematicsEngine
from martial_arts_ai.segmenter import MovementSegmenter
from martial_arts_ai.visualizer import OverlayRenderer, create_video_writer


def run_analyze(args: argparse.Namespace) -> None:
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[Error] Input video file not found: {input_path}")
        sys.exit(1)

    output_video_path = Path(args.output) if args.output else None
    output_json_path = Path(args.json_out) if args.json_out else None
    output_segments_path = Path(args.segments_out) if args.segments_out else None

    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        print(f"[Error] Could not open video: {input_path}")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0.0

    print("=" * 60)
    print(" Martial Arts Movement Analyzer - Video Pipeline")
    print("=" * 60)
    print(f" Input:      {input_path}")
    print(f" Resolution: {width}x{height} @ {fps:.2f} FPS")
    print(f" Duration:   {duration:.2f}s ({total_frames} frames)")
    if output_video_path and not args.no_video:
        print(f" Video Out:  {output_video_path}")
    if output_json_path:
        print(f" JSON Out:   {output_json_path}")
    print("=" * 60)

    # Initialize components
    detector = PoseDetector(
        model_path=args.model_path,
        enable_smoothing=not args.no_smoothing,
    )
    kinematics_engine = KinematicsEngine(use_world_coords=True)
    overlay_renderer = OverlayRenderer()

    writer = None
    codec_name = "none"
    if output_video_path and not args.no_video:
        writer, codec_name = create_video_writer(output_video_path, fps, width, height)
        print(f"[VideoWriter] Initialized with codec: {codec_name}")

    frame_analyses: List[Dict[str, Any]] = []
    detected_count = 0
    start_time = time.time()

    frame_idx = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            timestamp_ms = int(frame_idx * 1000.0 / fps)
            pose_data = detector.detect_frame(frame, timestamp_ms, frame_number=frame_idx)
            kinematics = kinematics_engine.analyze_frame(pose_data)

            if pose_data["person_detected"]:
                detected_count += 1

            frame_analyses.append(kinematics)

            if writer is not None:
                annotated = overlay_renderer.render_frame(frame, pose_data, kinematics)
                writer.write(annotated)

            frame_idx += 1
            if frame_idx % 60 == 0 or frame_idx == total_frames:
                pct = (frame_idx / total_frames) * 100.0 if total_frames > 0 else 0.0
                sys.stdout.write(f"\r Processing: {frame_idx}/{total_frames} frames ({pct:.1f}%)")
                sys.stdout.flush()

    finally:
        cap.release()
        if writer is not None:
            writer.release()
        detector.close()

    elapsed = time.time() - start_time
    proc_fps = frame_idx / elapsed if elapsed > 0 else 0.0
    print(f"\n Finished processing {frame_idx} frames in {elapsed:.2f}s ({proc_fps:.1f} FPS)")
    detection_pct = (detected_count / frame_idx * 100.0) if frame_idx > 0 else 0.0
    print(f" Person detected in {detected_count}/{frame_idx} frames ({detection_pct:.1f}%)")

    # Movement Segmentation
    segmenter = MovementSegmenter()
    segmentation_result = segmenter.segment_analysis(frame_analyses, fps=fps)
    print(f" Detected {segmentation_result['peaks_count']} candidate movement techniques.")

    # Save outputs
    if output_json_path:
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        analysis_payload = {
            "video": str(input_path),
            "fps": fps,
            "width": width,
            "height": height,
            "frame_count": frame_idx,
            "duration_seconds": duration,
            "detection_rate": round(detection_pct, 1),
            "frames": frame_analyses,
        }
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(analysis_payload, f, indent=2)
        print(f"[Export] Saved movement analysis to: {output_json_path}")

    if output_segments_path:
        output_segments_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_segments_path, "w", encoding="utf-8") as f:
            json.dump(segmentation_result, f, indent=2)
        print(f"[Export] Saved candidate segments to: {output_segments_path}")

    # Optional export to frontend/public/
    if getattr(args, "export_frontend", False):
        frontend_pub = Path("frontend/public")
        if frontend_pub.exists():
            if output_segments_path and output_segments_path.exists():
                shutil.copy(output_segments_path, frontend_pub / "movement_segments.json")
                print(f"[Export] Copied segments to {frontend_pub / 'movement_segments.json'}")
            if output_video_path and output_video_path.exists():
                shutil.copy(output_video_path, frontend_pub / "pose_output.mp4")
                print(f"[Export] Copied video to {frontend_pub / 'pose_output.mp4'}")


def run_live(args: argparse.Namespace) -> None:
    device_id = int(args.webcam)
    cap = cv2.VideoCapture(device_id)
    if not cap.isOpened():
        print(f"[Error] Could not access webcam device ID {device_id}")
        sys.exit(1)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    print("=" * 60)
    print(" Martial Arts AI - Live Webcam Analysis")
    print(f" Camera ID: {device_id} ({width}x{height})")
    print(" Press 'q' or ESC in the preview window to exit.")
    print("=" * 60)

    detector = PoseDetector(model_path=args.model_path, enable_smoothing=True)
    kinematics_engine = KinematicsEngine(use_world_coords=True)
    overlay_renderer = OverlayRenderer()

    start_wall = time.time()
    frame_idx = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[Live] Camera frame dropped.")
                break

            timestamp_ms = int((time.time() - start_wall) * 1000.0)
            pose_data = detector.detect_frame(frame, timestamp_ms, frame_number=frame_idx)
            kinematics = kinematics_engine.analyze_frame(pose_data)

            annotated = overlay_renderer.render_frame(
                frame,
                pose_data,
                kinematics,
                technique_label="LIVE WEBCAM",
            )

            cv2.imshow("Martial Arts AI - Live Telemetry", annotated)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q"), ord("Q")):
                break

            frame_idx += 1
    finally:
        cap.release()
        cv2.destroyAllWindows()
        detector.close()
        print("\n[Live] Session ended.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="martial-arts-ai",
        description="Biomechanical Movement Analyzer for Martial Arts.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: analyze
    p_analyze = subparsers.add_parser("analyze", help="Process an offline video file.")
    p_analyze.add_argument("--input", "-i", default="videos/test.mp4", help="Path to input video file.")
    p_analyze.add_argument("--output", "-o", default="videos/pose_output.mp4", help="Path for rendered video.")
    p_analyze.add_argument("--json-out", default="videos/movement_analysis.json", help="Path for kinematics JSON.")
    p_analyze.add_argument("--segments-out", default="videos/movement_segments.json", help="Path for segments JSON.")
    p_analyze.add_argument("--model-path", default="models/pose_landmarker_full.task", help="Path to MediaPipe model.")
    p_analyze.add_argument("--no-smoothing", action="store_true", help="Disable OneEuroFilter temporal smoothing.")
    p_analyze.add_argument("--no-video", action="store_true", help="Skip rendering output video.")
    p_analyze.add_argument("--export-frontend", action="store_true", help="Sync output files to frontend/public/.")

    # Subcommand: live
    p_live = subparsers.add_parser("live", help="Run real-time webcam telemetry.")
    p_live.add_argument("--webcam", "-w", type=int, default=0, help="Webcam device index (default: 0).")
    p_live.add_argument("--model-path", default="models/pose_landmarker_full.task", help="Path to MediaPipe model.")

    args = parser.parse_args()
    if args.command == "analyze":
        run_analyze(args)
    elif args.command == "live":
        run_live(args)


if __name__ == "__main__":
    main()

