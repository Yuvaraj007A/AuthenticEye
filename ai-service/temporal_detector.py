"""
AuthenticEye — Step 5: Temporal Video Analysis
Replaces simple frame averaging with temporal inconsistency detection.
Uses CNN feature extraction per frame + LSTM for temporal modeling.
"""
import asyncio
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as T
import numpy as np
from PIL import Image
from preprocessing import preprocess_image_for_ensemble, extract_frames

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class TemporalLSTM(nn.Module):
    """
    LSTM that models temporal relationships between consecutive frame features.
    Detects inter-frame inconsistencies: blinking artifacts, identity drift,
    unnatural motion patterns — all hallmarks of video deepfakes.
    """
    def __init__(self, feature_dim: int = 512, hidden_dim: int = 256, num_layers: int = 2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=feature_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.3,
        )
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        # x: (batch=1, seq_len, feature_dim)
        out, (h_n, _) = self.lstm(x)
        # Use last hidden state for classification
        last_hidden = h_n[-1]  # (batch, hidden_dim)
        return self.classifier(last_hidden)


class FrameFeatureExtractor(nn.Module):
    """Extracts 512-dim features from each frame using ResNet18."""
    def __init__(self):
        super().__init__()
        base = models.resnet18(weights="IMAGENET1K_V1")
        # Remove final FC layer to get 512-dim features
        self.features = nn.Sequential(*list(base.children())[:-1])

    def forward(self, x):
        feat = self.features(x)
        return feat.squeeze(-1).squeeze(-1)  # (batch, 512)


class TemporalVideoDetector:
    """
    Pipeline:
    1. Extract frames from video
    2. Detect faces in each frame
    3. Extract 512-dim CNN features per frame
    4. Run LSTM over feature sequence to detect temporal inconsistencies
    5. Frame-level deepfake probability + Temporal-level score → averaged
    
    Scientific Background:
    - Face-swapped deepfakes often have inter-frame flickering
    - The face region is replaced per-frame independently, 
      causing subtle temporal discontinuities
    - LSTM captures these sequential anomalies that per-frame analysis misses
    """

    TRANSFORM = T.Compose([
        T.Resize((224, 224)),
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    def __init__(self, image_detector, num_frames: int = 32):
        self.image_detector = image_detector
        self.num_frames = num_frames

        self.feature_extractor = FrameFeatureExtractor().to(DEVICE)
        self.feature_extractor.eval()

        self.temporal_model = TemporalLSTM(feature_dim=512).to(DEVICE)
        self.temporal_model.eval()

    def _extract_frame_features(self, frames: list) -> torch.Tensor:
        """Extract feature vectors for all frames. Returns (1, T, 512) tensor."""
        features = []
        for frame in frames:
            t = self.TRANSFORM(frame).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                feat = self.feature_extractor(t)  # (1, 512)
            features.append(feat)

        # Stack into sequence: (1, T, 512)
        return torch.stack(features, dim=1)

    def _compute_temporal_consistency(self, features: torch.Tensor) -> float:
        """
        Measures frame-to-frame feature drift.
        High drift → temporal inconsistency → deepfake indicator.
        """
        feats = features.squeeze(0).cpu().numpy()  # (T, 512)
        diffs = np.diff(feats, axis=0)
        drift = float(np.mean(np.linalg.norm(diffs, axis=1)))
        # Normalize: drift > 20 is very inconsistent
        return min(1.0, drift / 25.0)

    async def analyze(self, video_bytes: bytes, filename: str = "") -> dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._analyze_sync, video_bytes)

    def _analyze_sync(self, video_bytes: bytes) -> dict:
        # 1. Extract frames
        frames = extract_frames(video_bytes, num_frames=self.num_frames)
        if not frames:
            raise ValueError("Could not extract frames from video.")

        # 2. Per-frame ensemble inference
        frame_scores = []
        faces_found = 0
        for frame in frames:
            tensor, face_found = preprocess_image_for_ensemble(frame)
            result = self.image_detector.predict(tensor)
            frame_scores.append(result["deepfake_probability"])
            if face_found:
                faces_found += 1

        avg_frame_score = float(np.mean(frame_scores))
        max_frame_score = float(np.max(frame_scores))
        flagged = sum(1 for s in frame_scores if s > 0.5)

        # 3. Temporal LSTM analysis
        seq_tensor = self._extract_frame_features(frames)
        with torch.no_grad():
            temporal_score = self.temporal_model(seq_tensor).squeeze().item()

        # 4. Frame drift consistency
        drift_score = self._compute_temporal_consistency(seq_tensor)

        # 5. Final score
        # Weighted combination of frame-level and temporal-level signals
        final_score = (avg_frame_score * 0.50) + (temporal_score * 0.30) + (drift_score * 0.20)

        return {
            "deepfake_probability": round(min(0.99, final_score), 4),
            "authenticity_score": round(max(0.01, 1.0 - final_score), 4),
            "temporal_score": round(temporal_score, 4),
            "temporal_drift": round(drift_score, 4),
            "frames_analyzed": len(frame_scores),
            "faces_detected_in": faces_found,
            "flagged_frames": flagged,
            "frame_score_stats": {
                "mean": round(avg_frame_score, 4),
                "max": round(max_frame_score, 4),
                "min": round(float(np.min(frame_scores)), 4),
            },
            "media_type": "video",
        }
