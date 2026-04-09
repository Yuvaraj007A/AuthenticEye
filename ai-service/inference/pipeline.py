import torch
import torch.nn as nn
from PIL import Image
import albumentations as A
import numpy as np
from albumentations.pytorch import ToTensorV2
import sys
import time
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

# Assuming models, features, fusion are imported relative to ai-service root
sys.path.append(str(Path(__file__).parent.parent))

from models.image_models import EfficientNetDetector, XceptionDetector, ViTDetector
from models.video_temporal import VideoTemporalLSTM
from features.signal_extractors import FFTExtractor, GANFingerprintExtractor, DiffusionExtractor
from features.clip_extractor import CLIPFeatureExtractor
from fusion.fusion_model import AuthenticEyeFusionMLP

class AuthenticEyePipeline:
    """
    End-to-End Orchestrator for AuthenticEye Inference.
    Extracts all features, runs through base models, and outputs final fusion logic.
    """
    def __init__(self, checkpoints_dir="../checkpoints"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print("Initializing AuthenticEye v2 Pipeline...")
        
        # 1. Base Image Models
        self.eff = EfficientNetDetector(pretrained=False).to(self.device).eval()
        self.xcep = XceptionDetector(pretrained=False).to(self.device).eval()
        self.vit = ViTDetector(pretrained=False).to(self.device).eval()
        
        # 2. Featue Extractors
        self.fft_ext = FFTExtractor()
        self.gan_ext = GANFingerprintExtractor()
        self.diff_ext = DiffusionExtractor()
        self.clip_ext = CLIPFeatureExtractor()
        
        # 3. Fusion & Video
        self.fusion_mlp = AuthenticEyeFusionMLP(input_dim=16).to(self.device).eval()
        self.video_lstm = VideoTemporalLSTM(input_dim=16).to(self.device).eval()
        
        # Standard transform for base models
        self.transform = A.Compose([
            A.Resize(height=224, width=224),
            A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
            ToTensorV2(),
        ])
        
        self.load_checkpoints(checkpoints_dir)
        
    def load_checkpoints(self, ckpt_dir):
        """Loads weights for all trainable models if available."""
        models = {
            "efficientnet_b4_best.pth": self.eff,
            "xceptionnet_best.pth": self.xcep,
            "vit_best.pth": self.vit,
            "fusion_mlp.pth": self.fusion_mlp,
            "video_lstm.pth": self.video_lstm
        }
        
        import os
        for fname, model in models.items():
            path = os.path.join(ckpt_dir, fname)
            if os.path.exists(path):
                try:
                    ckpt = torch.load(path, map_location=self.device)
                    # Handle state dict wrapped in 'model_state'
                    if isinstance(ckpt, dict) and 'model_state' in ckpt:
                        model.load_state_dict(ckpt['model_state'])
                    else:
                        model.load_state_dict(ckpt)
                    print(f"Loaded: {fname}")
                except Exception as e:
                    print(f"Failed to load {fname}: {e}")
            else:
                print(f"Checkpoint not found for {fname}, using raw initialization.")

    def extract_features(self, pil_img: Image.Image) -> list[float]:
        """Runs all models and extractors on a single image to produce the 16-dim vector."""
        # 1. Base Model Logits
        img_np = np.array(pil_img.convert("RGB"))
        tensor = self.transform(image=img_np)['image'].unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            logit_eff = self.eff(tensor).item()
            logit_xcep = self.xcep(tensor).item()
            logit_vit = self.vit(tensor).item()
            
        # 2. Statistical Extractors
        fft_feats = self.fft_ext.extract(pil_img)
        gan_feats = self.gan_ext.extract(pil_img)
        diff_feats = self.diff_ext.extract(pil_img)
        
        # 3. CLIP Embeddings Match
        clip_feats = self.clip_ext.extract(pil_img)
        
        # Combine all to size 16
        feature_vector = (
            [logit_eff, logit_xcep, logit_vit] +
            fft_feats +
            gan_feats +
            diff_feats +
            clip_feats
        )
        return feature_vector

    def predict_image(self, pil_img: Image.Image) -> dict:
        """Fully processes an image to predict deepfake probability."""
        start_time = time.time()
        features = self.extract_features(pil_img)
        vec = torch.FloatTensor(features).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            fusion_logit = self.fusion_mlp(vec).item()
            
        # Convert logit to probability
        prob = 1.0 / (1.0 + np.exp(-fusion_logit))
        analysis_time = time.time() - start_time
        
        return {
            "result": "Fake (Synthetically Generated)" if prob > 0.5 else "Real (Authentic Media)",
            "analysis_time_seconds": round(analysis_time, 4),
            "features_extracted": [round(f, 4) for f in features]
        }
        
    def predict_video(self, frame_list: list[Image.Image]) -> dict:
        """Processes a sequence of frames for video prediction."""
        if not frame_list:
            return {"result": "Unknown", "analysis_time_seconds": 0.0}
            
        start_time = time.time()
        # Extract features per frame
        features_seq = []
        for frame in frame_list:
            features = self.extract_features(frame)
            features_seq.append(features)
            
        vec = torch.FloatTensor(features_seq).unsqueeze(0).to(self.device) # Batch=1
        
        with torch.no_grad():
            video_logit = self.video_lstm(vec).item()
            
        prob = 1.0 / (1.0 + np.exp(-video_logit))
        analysis_time = time.time() - start_time

        return {
            "result": "Fake (Synthetically Generated)" if prob > 0.5 else "Real (Authentic Media)",
            "analysis_time_seconds": round(analysis_time, 4),
        }

# Example usage:
if __name__ == "__main__":
    pipeline = AuthenticEyePipeline()
    img = Image.new("RGB", (224, 224), color="white")
    res = pipeline.predict_image(img)
    print("Test Image Output:")
    print(res)
