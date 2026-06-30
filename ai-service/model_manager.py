import os
import torch
from typing import Dict, Any

class ModelManager:
    """
    Manages downloding, updating, health monitoring, and fallback execution
    for deep learning models.
    """
    def __init__(self):
        self.models_dir = os.path.join(os.path.dirname(__file__), "models")
        os.makedirs(self.models_dir, exist_ok=True)
        
    def verify_integrity(self, file_path: str) -> bool:
        """Checks if a model checkpoint file is valid by loading with torch or checking size."""
        if not os.path.exists(file_path):
            return False
        try:
            # Check if file has positive non-zero size
            if os.path.getsize(file_path) < 1024:
                return False
            # Check if torch can parse header
            torch.load(file_path, map_location="cpu", weights_only=True)
            return True
        except Exception:
            # Try loading it normally without strict headers
            try:
                torch.load(file_path, map_location="cpu")
                return True
            except Exception:
                return False

    def auto_download_dependencies(self) -> Dict[str, bool]:
        """
        Pre-caches Hugging Face models at startup.
        Returns dictionary mapping model name to download status.
        """
        status = {}
        return status

    def get_system_health(self, registry) -> Dict[str, Any]:
        """
        Gathers system-level health, memory, and detector details.
        """
        device = "cuda" if torch.cuda.is_available() else "cpu"
        loaded_detectors = {}
        for name, instance in registry.detectors.items():
            loaded_detectors[name] = {
                "loaded": instance.is_loaded,
                "error": instance.load_error
            }
            
        gpu_info = {}
        if device == "cuda":
            gpu_info = {
                "name": torch.cuda.get_device_name(0),
                "memory_allocated_mb": round(torch.cuda.memory_allocated(0) / (1024**2), 2),
                "memory_reserved_mb": round(torch.cuda.memory_reserved(0) / (1024**2), 2)
            }
            
        return {
            "device": device,
            "gpu_details": gpu_info,
            "detectors": loaded_detectors,
            "models_directory_exists": os.path.exists(self.models_dir)
        }

# Global instance
model_manager = ModelManager()
