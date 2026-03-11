"""
AuthenticEye — Video Deepfake Detector
Pipeline: Upload → Extract Frames → Detect Faces → Run Model → Aggregate
"""
import asyncio
import numpy as np
from PIL import Image
from preprocessing import preprocess_image_for_ensemble, extract_frames


class VideoDeepfakeDetector:
    """
    Analyzes video by:
    1. Extracting evenly-spaced frames (default 32)
    2. Running ensemble image detector on each frame
    3. Averaging predictions for final verdict
    """

    def __init__(self, image_detector, num_frames: int = 32):
        self.image_detector = image_detector
        self.num_frames = num_frames

    async def analyze(self, video_bytes: bytes, filename: str = "") -> dict:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, self._analyze_sync, video_bytes
        )
        return result

    def _analyze_sync(self, video_bytes: bytes) -> dict:
        frames = extract_frames(video_bytes, num_frames=self.num_frames)

        if not frames:
            raise ValueError("Could not extract frames from video.")

        frame_scores = []
        faces_found = 0

        for frame in frames:
            tensor, face_found = preprocess_image_for_ensemble(frame)
            result = self.image_detector.predict(tensor)
            frame_scores.append(result["deepfake_probability"])
            if face_found:
                faces_found += 1

        # Aggregate frame scores
        avg_prob = float(np.mean(frame_scores))
        max_prob = float(np.max(frame_scores))
        min_prob = float(np.min(frame_scores))

        # If most frames flag as fake, overall is fake
        flagged_frames = sum(1 for s in frame_scores if s > 0.5)
        frame_verdict_ratio = flagged_frames / len(frame_scores)

        # Final weighted score: average + boost if many frames flagged
        final_prob = avg_prob * 0.7 + frame_verdict_ratio * 0.3

        return {
            "deepfake_probability": round(min(0.99, final_prob), 4),
            "authenticity_score": round(max(0.01, 1.0 - final_prob), 4),
            "frames_analyzed": len(frame_scores),
            "faces_detected_in": faces_found,
            "flagged_frames": flagged_frames,
            "frame_score_stats": {
                "mean": round(avg_prob, 4),
                "max": round(max_prob, 4),
                "min": round(min_prob, 4),
            },
            "media_type": "video",
        }
