import os
import torch
from PIL import Image
from detectors.base import BaseDetector
from model import XceptionDetector
from preprocessing import preprocess_image_for_ensemble

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class XceptionFFPP(BaseDetector):
    """
    XceptionNet detector fine-tuned on the FaceForensics++ (FF++) dataset.
    """
    def _load_model(self) -> bool:
        self.model = XceptionDetector(pretrained=False).to(DEVICE)
        
        # Paths to search for weights (from model.py)
        models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
        checkpoints_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "checkpoints")
        
        xcep_paths = [
            os.path.join(models_dir, "xception_ffpp.pt"),
            os.path.join(checkpoints_dir, "xceptionnet.pth"),
            os.path.join(checkpoints_dir, "xceptionnet_best.pth")
        ]
        
        loaded = False
        for p in xcep_paths:
            if os.path.exists(p):
                try:
                    state = torch.load(p, map_location=DEVICE)
                    if isinstance(state, dict) and "model_state" in state:
                        state = state["model_state"]
                    self.model.load_state_dict(state, strict=False)
                    print(f"[XceptionFFPP] Loaded weights from {p}")
                    loaded = True
                    break
                except Exception as e:
                    print(f"[XceptionFFPP] Failed to load {p}: {e}")
                    
        if not loaded:
            print("[XceptionFFPP] WARNING: Using default ImageNet weights for baseline prediction.")
            self.model = XceptionDetector(pretrained=True).to(DEVICE)
            
        self.model.eval()
        return True

    def _predict(self, pil_image: Image.Image, **kwargs) -> dict:
        tensor, face_found = preprocess_image_for_ensemble(pil_image)
        tensor = tensor.to(DEVICE)
        
        with torch.no_grad():
            output = self.model(tensor)
            # XceptionDetector returns sigmoid activated values in model.py
            score = float(output.squeeze().item())
            
        confidence = abs(score - 0.5) * 2
        return {
            "score": score,
            "confidence": confidence,
            "details": {
                "face_detected": face_found
            }
        }
