import os
import cv2
import tempfile
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as T
import numpy as np
from PIL import Image
from typing import List, Tuple
from detectors.base import BaseDetector

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Re-use standard models from models/video_temporal.py and main models
class FrameFeatureExtractor(nn.Module):
    def __init__(self):
        super().__init__()
        base = models.resnet18(weights="IMAGENET1K_V1")
        self.features = nn.Sequential(*list(base.children())[:-1])

    def forward(self, x):
        feat = self.features(x)
        return feat.squeeze(-1).squeeze(-1) # (batch, 512)

class VideoTemporalLSTM(nn.Module):
    def __init__(self, input_dim=512, hidden_dim=256, num_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.3
        )
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        out, (h_n, _) = self.lstm(x)
        last_hidden = h_n[-1]
        return self.classifier(last_hidden)

class TemporalVideoAnalyzer(BaseDetector):
    """
    Temporal video analyzer checking:
    1. Optical Flow motion consistency (Farneback flow)
    2. Embedding consistency tracking (cosine similarity of ResNet features)
    3. Sequence modeling via LSTM (VideoTemporalLSTM)
    """
    def __init__(self):
        super().__init__()
        self.feature_extractor = None
        self.lstm_model = None
        self.num_frames = 32
        
        self.transform = T.Compose([
            T.Resize((224, 224)),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    def _load_model(self) -> bool:
        self.feature_extractor = FrameFeatureExtractor().to(DEVICE)
        self.feature_extractor.eval()
        
        self.lstm_model = VideoTemporalLSTM(input_dim=512).to(DEVICE)
        self.lstm_model.eval()
        
        # Load pre-trained video temporal checkpoint if exists
        models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
        lstm_path = os.path.join(models_dir, "video_temporal.pt")
        if os.path.exists(lstm_path):
            try:
                self.lstm_model.load_state_dict(torch.load(lstm_path, map_location=DEVICE), strict=False)
                print(f"[TemporalVideoAnalyzer] Loaded LSTM weights from {lstm_path}")
            except Exception as e:
                print(f"[TemporalVideoAnalyzer] Failed to load LSTM weights: {e}")
                
        return True

    def _extract_adaptive_frames(self, video_bytes: bytes) -> List[Image.Image]:
        """
        Extract frames adaptively based on scene-change detection (histogram diff).
        Always samples up to self.num_frames.
        """
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(video_bytes)
            tmp_path = f.name

        cap = cv2.VideoCapture(tmp_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if total_frames <= 0:
            cap.release()
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            return []

        # We first do a pass to compute color histogram changes between adjacent frames
        step = max(1, total_frames // (self.num_frames * 2))
        histograms = []
        frame_indices = []
        
        for idx in range(0, total_frames, step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret:
                break
            
            # Compute HSV color histogram
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [8, 8], [0, 180, 0, 256])
            cv2.normalize(hist, hist)
            histograms.append((idx, hist))
            
        # Detect scene changes where histogram correlation drops significantly
        transitions = []
        for i in range(1, len(histograms)):
            corr = cv2.compareHist(histograms[i-1][1], histograms[i][1], cv2.HISTCMP_CORREL)
            # Correlation closer to 0 indicates high discrepancy / transition
            transitions.append((histograms[i][0], 1.0 - corr))
            
        # Select the top frame indices representing transitions + fallback evenly-spaced frames
        transitions.sort(key=lambda x: x[1], reverse=True)
        selected_indices = [t[0] for t in transitions[:self.num_frames // 2]]
        
        # Add even sampling
        even_indices = np.linspace(0, total_frames - 1, self.num_frames // 2, dtype=int)
        all_indices = sorted(list(set(selected_indices).union(set(even_indices))))
        
        # Ensure we don't exceed num_frames
        if len(all_indices) > self.num_frames:
            all_indices = [all_indices[int(i)] for i in np.linspace(0, len(all_indices) - 1, self.num_frames)]
        elif len(all_indices) < self.num_frames:
            # Pad
            additional = np.linspace(0, total_frames - 1, self.num_frames - len(all_indices), dtype=int)
            all_indices = sorted(list(set(all_indices).union(set(additional))))
            
        # Extract the frames
        frames = []
        for idx in all_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
            ret, frame = cap.read()
            if ret:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(Image.fromarray(rgb))
                
        cap.release()
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
            
        return frames

    def _compute_optical_flow_score(self, frames: List[Image.Image]) -> float:
        """
        Computes dense optical flow (Farneback) on consecutive frames.
        Returns a normalized motion anomaly score.
        """
        if len(frames) < 2:
            return 0.0
            
        flow_magnitudes = []
        
        # Convert first frame to grayscale and resize to standard size for speed
        prev_img = np.array(frames[0].resize((128, 128)).convert("L"))
        
        for i in range(1, len(frames)):
            curr_img = np.array(frames[i].resize((128, 128)).convert("L"))
            
            # Compute dense optical flow
            flow = cv2.calcOpticalFlowFarneback(
                prev_img, curr_img, None, 0.5, 3, 15, 3, 5, 1.2, 0
            )
            
            # Compute flow magnitude
            magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
            flow_magnitudes.append(np.mean(magnitude))
            prev_img = curr_img
            
        # Compute standard deviation / peak changes in motion vector magnitudes.
        # High deviation indicates chaotic motion / temporal flicker.
        mean_flow = np.mean(flow_magnitudes)
        std_flow = np.std(flow_magnitudes)
        
        # Normalize: mean flow > 4.0 or std flow > 2.0 indicates motion consistency issue
        motion_score = min(1.0, (mean_flow * 0.15) + (std_flow * 0.25))
        return float(motion_score)

    def _compute_embedding_consistency_score(self, feature_sequence: torch.Tensor) -> float:
        """
        Tracks cosine similarity between consecutive frame features.
        Returns a normalized identity drift score.
        """
        feats = feature_sequence.squeeze(0) # (T, 512)
        
        # Compute cosine similarities between adjacents
        similarities = []
        for i in range(1, len(feats)):
            v1 = feats[i-1]
            v2 = feats[i]
            sim = torch.cosine_similarity(v1.unsqueeze(0), v2.unsqueeze(0)).item()
            similarities.append(sim)
            
        # Standard deviation of similarities (real videos are highly consistent, i.e., std close to 0)
        # Deepfakes experience identity drops/jumps causing high variance
        std_sim = np.std(similarities)
        mean_sim = np.mean(similarities)
        
        # High identity drift corresponds to low mean similarity and high variance
        drift_score = min(1.0, max(0.0, (1.0 - mean_sim) * 3.0 + std_sim * 4.0))
        return float(drift_score)

    def _predict(self, pil_image: Image.Image, **kwargs) -> dict:
        # Fallback: if we just get a single image, temporal analysis is 0
        return {
            "score": 0.0,
            "confidence": 1.0,
            "details": {
                "message": "Temporal analysis requires a video stream"
            }
        }

    def predict_video(self, video_bytes: bytes) -> dict:
        """
        Performs the complete temporal analysis workflow:
        1. Scene-aware frame selection.
        2. Sequence feature extraction.
        3. Optical flow calculation.
        4. Embedding cosine similarity checking.
        5. Temporal LSTM sequence modeling.
        """
        if not self.is_loaded:
            self.load()
            
        # Extract frames
        frames = self._extract_adaptive_frames(video_bytes)
        if not frames:
            raise ValueError("No frames could be extracted from the video file.")
            
        # Compute Optical Flow
        flow_score = self._compute_optical_flow_score(frames)
        
        # Extract frame features
        features = []
        for frame in frames:
            t = self.transform(frame).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                feat = self.feature_extractor(t)
            features.append(feat)
            
        seq_tensor = torch.stack(features, dim=1) # (1, T, 512)
        
        # Compute Embedding Drift
        drift_score = self._compute_embedding_consistency_score(seq_tensor)
        
        # Run Temporal LSTM
        with torch.no_grad():
            lstm_logit = self.lstm_model(seq_tensor).squeeze().item()
            
        # Blend the three scores into a single Temporal Score
        # LSTM prediction: 50%
        # Optical flow motion anomaly: 30%
        # Embedding identity drift: 20%
        temporal_score = (lstm_logit * 0.50) + (flow_score * 0.30) + (drift_score * 0.20)
        temporal_score = min(0.99, max(0.01, temporal_score))
        
        return {
            "score": temporal_score,
            "confidence": abs(temporal_score - 0.5) * 2,
            "details": {
                "lstm_probability": round(lstm_logit, 4),
                "optical_flow_anomaly": round(flow_score, 4),
                "embedding_drift": round(drift_score, 4),
                "frames_analyzed": len(frames)
            }
        }
