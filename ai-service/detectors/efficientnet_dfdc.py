import os
import torch
import torchvision.transforms as T
from PIL import Image
from detectors.base import BaseDetector
from model import EfficientNetDetector
from preprocessing import preprocess_image_for_ensemble

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class EfficientNetDFDC(BaseDetector):
    """
    EfficientNet-B4 detector fine-tuned on the Deepfake Detection Challenge (DFDC) dataset.
    """
    def _load_model(self) -> bool:
        self.model = EfficientNetDetector(pretrained=False).to(DEVICE)
        
        # Paths to search for weights (from model.py)
        models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
        checkpoints_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "checkpoints")
        
        eff_paths = [
            os.path.join(models_dir, "efficientnet_dfdc.pt"),
            os.path.join(checkpoints_dir, "efficientnet_b4.pth"),
            os.path.join(checkpoints_dir, "efficientnet_b4_best.pth")
        ]
        
        loaded = False
        for p in eff_paths:
            if os.path.exists(p):
                try:
                    state = torch.load(p, map_location=DEVICE)
                    if isinstance(state, dict) and "model_state" in state:
                        state = state["model_state"]
                    self.model.load_state_dict(state, strict=False)
                    print(f"[EfficientNetDFDC] Loaded weights from {p}")
                    loaded = True
                    break
                except Exception as e:
                    print(f"[EfficientNetDFDC] Failed to load {p}: {e}")
                    
        if not loaded:
            print("[EfficientNetDFDC] WARNING: Using default ImageNet weights for baseline prediction.")
            self.model = EfficientNetDetector(pretrained=True).to(DEVICE)
            
        self.model.eval()
        return True

    def _predict(self, pil_image: Image.Image, **kwargs) -> dict:
        # Preprocess input image using existing preprocessing utils
        tensor, face_found = preprocess_image_for_ensemble(pil_image)
        tensor = tensor.to(DEVICE)
        
        with torch.no_grad():
            output = self.model(tensor)
            # EfficientNetDetector returns sigmoid activated values in model.py
            score = float(output.squeeze().item())
            
        confidence = abs(score - 0.5) * 2
        return {
            "score": score,
            "confidence": confidence,
            "details": {
                "face_detected": face_found
            }
        }

    def get_primary_model(self):
        """Returns the primary model for Grad-CAM overlay generation."""
        return self.model
