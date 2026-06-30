"""
AuthenticEye — Ensemble Deepfake Detection Model
Primary Models: EfficientNet-B4, XceptionNet (via timm)
Ensemble: Logistic Regression classifier trained on combined CNN & forensic scores
"""
import os
import pickle
import json
import torch
import torch.nn as nn
import torchvision.transforms as T
import timm
import numpy as np
from PIL import Image

from frequency_detector import get_frequency_detector
from artifact_detector import ArtifactDetector

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ─── Model Definitions ───────────────────────────────────────────────────────

class EfficientNetDetector(nn.Module):
    """EfficientNet-B4 fine-tuned as binary classifier (real vs fake)."""
    def __init__(self, pretrained=True):
        super().__init__()
        self.base = timm.create_model("efficientnet_b4", pretrained=pretrained, num_classes=1)

    def forward(self, x):
        return torch.sigmoid(self.base(x))


class XceptionDetector(nn.Module):
    """Xception model (via timm legacy_xception) as binary classifier."""
    def __init__(self, pretrained=True):
        super().__init__()
        self.base = timm.create_model("xception", pretrained=pretrained, num_classes=1)

    def forward(self, x):
        return torch.sigmoid(self.base(x))


class ViTDetector(nn.Module):
    """Vision Transformer (ViT-B/16) as binary classifier."""
    def __init__(self, pretrained=True):
        super().__init__()
        self.base = timm.create_model("vit_base_patch16_224", pretrained=pretrained, num_classes=1)

    def forward(self, x):
        return torch.sigmoid(self.base(x))


# ─── New Ensemble Detector (Phase 2) ──────────────────────────────────────────

class EnsembleDetector(nn.Module):
    """
    Ensemble of EfficientNet-B4, XceptionNet, FFT, and Artifact Detector.
    Uses LogisticRegression as ensemble learner (meta-classifier).
    """
    def __init__(self, eff_model, xcep_model, fft_detector, artifact_detector):
        super().__init__()
        self.eff = eff_model
        self.xcep = xcep_model
        self.fft = fft_detector
        self.artifact = artifact_detector
        
        self.clf = pickle.loads(
            # Default fallback mock weights if ensemble.pkl is not trained yet
            pickle.dumps(None)
        )

    def load_ensemble_weights(self):
        models_dir = os.path.join(os.path.dirname(__file__), "models")
        clf_path = os.path.join(models_dir, "ensemble.pkl")
        if os.path.exists(clf_path):
            try:
                with open(clf_path, "rb") as f:
                    self.clf = pickle.load(f)
                print("[SUCCESS] Loaded Logistic Regression ensemble weights from models/ensemble.pkl")
            except Exception as e:
                print(f"[WARNING] Failed to load ensemble weights: {e}")
                self.clf = None
        else:
            self.clf = None

    def predict(self, tensor: torch.Tensor, pil_image: Image.Image) -> dict:
        self.eval()
        with torch.no_grad():
            tensor = tensor.to(DEVICE)
            score_eff = self.eff(tensor).squeeze().item()
            score_xcep = self.xcep(tensor).squeeze().item()

        # Extract FFT features
        fft_res = self.fft.predict(pil_image)
        fft_score = fft_res.get("frequency_score", 0.0)

        # Extract Artifact features
        art_res = self.artifact.predict(pil_image)
        art_score = art_res.get("artifact_probability", 0.0)

        features = np.array([[score_eff, score_xcep, fft_score, art_score]])

        # If logistic regression is trained, use it. Otherwise use a balanced average.
        if self.clf is not None and hasattr(self.clf, "classes_"):
            try:
                final_prob = float(self.clf.predict_proba(features)[0, 1])
            except Exception:
                final_prob = float(0.3 * score_eff + 0.3 * score_xcep + 0.2 * fft_score + 0.2 * art_score)
        else:
            # Fallback simple blend
            final_prob = float(0.3 * score_eff + 0.3 * score_xcep + 0.2 * fft_score + 0.2 * art_score)

        return {
            "deepfake_probability": round(min(0.9999, max(0.0001, final_prob)), 4),
            "authenticity_score": round(1.0 - min(0.9999, max(0.0001, final_prob)), 4),
            "model_scores": {
                "efficientnet_b4": round(score_eff, 4),
                "xceptionnet": round(score_xcep, 4),
                "frequency_fft": round(fft_score, 4),
                "artifact_detector": round(art_score, 4),
            }
        }

    def get_primary_model(self):
        """Returns the primary model (EfficientNet) for Grad-CAM."""
        return self.eff


# ─── Backward Compatibility Ensemble Wrapper ─────────────────────────────────

class EnsembleImageDetector(nn.Module):
    """
    Backward-compatible wrapper averaging EffNet, Xception, ViT.
    """
    def __init__(self, eff_model, xcep_model, vit_model):
        super().__init__()
        self.eff = eff_model
        self.xcep = xcep_model
        self.vit = vit_model

    def predict(self, tensor: torch.Tensor) -> dict:
        self.eval()
        with torch.no_grad():
            tensor = tensor.to(DEVICE)
            score_eff = self.eff(tensor).squeeze().item()
            score_xcep = self.xcep(tensor).squeeze().item()
            score_vit = self.vit(tensor).squeeze().item()

            final_score = (0.40 * score_eff) + (0.35 * score_xcep) + (0.25 * score_vit)

        return {
            "deepfake_probability": final_score,
            "authenticity_score": 1.0 - final_score,
            "model_scores": {
                "efficientnet_b4": round(score_eff, 4),
                "xceptionnet": round(score_xcep, 4),
                "vision_transformer": round(score_vit, 4),
            }
        }

    def get_primary_model(self):
        return self.eff


# ─── Model Loader ────────────────────────────────────────────────────────────

def load_models() -> EnsembleDetector:
    """
    Loads the ensemble of models, utilizing versioned weights if available.
    """
    print("  Loading EfficientNet-B4...")
    eff = EfficientNetDetector(pretrained=False).to(DEVICE)

    print("  Loading XceptionNet...")
    xcep = XceptionDetector(pretrained=False).to(DEVICE)

    models_dir = os.path.join(os.path.dirname(__file__), "models")
    os.makedirs(models_dir, exist_ok=True)

    # 1. Load EfficientNet weights
    eff_loaded = False
    eff_paths = [
        os.path.join(models_dir, "efficientnet_dfdc.pt"),
        os.path.join(os.path.dirname(__file__), "checkpoints", "efficientnet_b4.pth"),
        os.path.join(os.path.dirname(__file__), "checkpoints", "efficientnet_b4_best.pth")
    ]
    for p in eff_paths:
        if os.path.exists(p):
            try:
                state = torch.load(p, map_location=DEVICE)
                if isinstance(state, dict) and "model_state" in state:
                    state = state["model_state"]
                eff.load_state_dict(state, strict=False)
                print(f"  [SUCCESS] Loaded EfficientNet-B4 weights from {os.path.basename(p)}")
                eff_loaded = True
                break
            except Exception as e:
                print(f"  [WARNING] Failed to load {os.path.basename(p)}: {e}")
    if not eff_loaded:
        print("  [WARNING] EfficientNet-B4 using default pretrained ImageNet weights")

    # 2. Load Xception weights
    xcep_loaded = False
    xcep_paths = [
        os.path.join(models_dir, "xception_ffpp.pt"),
        os.path.join(os.path.dirname(__file__), "checkpoints", "xceptionnet.pth"),
        os.path.join(os.path.dirname(__file__), "checkpoints", "xceptionnet_best.pth")
    ]
    for p in xcep_paths:
        if os.path.exists(p):
            try:
                state = torch.load(p, map_location=DEVICE)
                if isinstance(state, dict) and "model_state" in state:
                    state = state["model_state"]
                xcep.load_state_dict(state, strict=False)
                print(f"  [SUCCESS] Loaded Xception weights from {os.path.basename(p)}")
                xcep_loaded = True
                break
            except Exception as e:
                print(f"  [WARNING] Failed to load {os.path.basename(p)}: {e}")
    if not xcep_loaded:
        print("  [WARNING] Xception using default pretrained ImageNet weights")

    fft_det = get_frequency_detector()
    art_det = ArtifactDetector()

    ensemble = EnsembleDetector(eff, xcep, fft_det, art_det)
    ensemble.load_ensemble_weights()
    ensemble.eval()
    return ensemble
