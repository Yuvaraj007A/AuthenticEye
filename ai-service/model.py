"""
AuthenticEye — Ensemble Deepfake Detection Model
Primary Models: EfficientNet-B4, XceptionNet (via timm), Vision Transformer
Ensemble: Average of all three models
"""
import torch
import torch.nn as nn
import torchvision.transforms as T
import timm
import numpy as np

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ─── Model Definitions ───────────────────────────────────────────────────────

class EfficientNetDetector(nn.Module):
    """EfficientNet-B4 fine-tuned as binary classifier (real vs fake)."""
    def __init__(self):
        super().__init__()
        self.base = timm.create_model("efficientnet_b4", pretrained=True, num_classes=1)

    def forward(self, x):
        return torch.sigmoid(self.base(x))


class XceptionDetector(nn.Module):
    """Xception model (via timm legacy_xception) as binary classifier."""
    def __init__(self):
        super().__init__()
        self.base = timm.create_model("xception", pretrained=True, num_classes=1)

    def forward(self, x):
        return torch.sigmoid(self.base(x))


class ViTDetector(nn.Module):
    """Vision Transformer (ViT-B/16) as binary classifier."""
    def __init__(self):
        super().__init__()
        self.base = timm.create_model("vit_base_patch16_224", pretrained=True, num_classes=1)

    def forward(self, x):
        return torch.sigmoid(self.base(x))


# ─── Ensemble Wrapper ────────────────────────────────────────────────────────

class EnsembleImageDetector(nn.Module):
    """
    Ensemble of EfficientNet-B4, XceptionNet, and ViT.
    Final score = weighted average:
      final = 0.40 * eff + 0.35 * xcep + 0.25 * vit
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

            # Weighted ensemble
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
        """Returns the primary model (EfficientNet) for Grad-CAM."""
        return self.eff


# ─── Model Loader ────────────────────────────────────────────────────────────

def load_models() -> EnsembleImageDetector:
    """
    Loads the ensemble of models.
    In production, you would load fine-tuned weights trained on
    FaceForensics++, DFDC, or Celeb-DF datasets.
    Currently loads ImageNet pretrained weights as base.
    To fine-tune: run training/train.py
    """
    print("  Loading EfficientNet-B4...")
    eff = EfficientNetDetector().to(DEVICE)

    print("  Loading XceptionNet...")
    xcep = XceptionDetector().to(DEVICE)

    print("  Loading Vision Transformer...")
    vit = ViTDetector().to(DEVICE)

    # Load fine-tuned checkpoints if available
    checkpoint_dir = os.environ.get("CHECKPOINT_DIR", "./checkpoints")
    for name, model_obj, fname in [
        ("efficientnet_b4", eff, "efficientnet_b4.pth"),
        ("xceptionnet", xcep, "xceptionnet.pth"),
        ("vit", vit, "vit.pth"),
    ]:
        ckpt_path = f"{checkpoint_dir}/{fname}"
        if os.path.exists(ckpt_path):
            state = torch.load(ckpt_path, map_location=DEVICE)
            model_obj.load_state_dict(state, strict=False)
            print(f"  ✅ Loaded checkpoint: {fname}")
        else:
            print(f"  ⚠️  No checkpoint for {name} — using pretrained ImageNet weights")

    ensemble = EnsembleImageDetector(eff, xcep, vit)
    ensemble.eval()
    return ensemble


import os
