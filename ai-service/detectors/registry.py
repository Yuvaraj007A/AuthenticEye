import os
import json
import importlib
import sys
from PIL import Image
from typing import Dict, List, Any

# Ensure detectors directory is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from detectors.base import BaseDetector

class DetectorRegistry:
    """
    Manages loading, hot-reloading, and execution of all registered detectors.
    """
    def __init__(self):
        self.detectors: Dict[str, BaseDetector] = {}
        self.detector_classes = {}
        
    def register(self, name: str, detector_cls):
        """Register a detector class under a given name."""
        self.detector_classes[name] = detector_cls
        print(f"[REGISTRY] Registered detector class: {name}")

    def load_all(self):
        """Instantiate and load all registered detectors."""
        for name, cls in self.detector_classes.items():
            if name not in self.detectors:
                try:
                    detector_instance = cls()
                    detector_instance.load()
                    self.detectors[name] = detector_instance
                except Exception as e:
                    print(f"[REGISTRY] Error instantiating {name}: {e}")

    def get_detector(self, name: str) -> BaseDetector:
        """Retrieve a loaded detector instance, loading it on-demand if needed."""
        if name not in self.detectors and name in self.detector_classes:
            try:
                detector_instance = self.detector_classes[name]()
                detector_instance.load()
                self.detectors[name] = detector_instance
            except Exception as e:
                print(f"[REGISTRY] Error lazy loading {name}: {e}")
                return None
        return self.detectors.get(name)

    def predict_all(self, pil_image: Image.Image, **kwargs) -> Dict[str, Dict[str, Any]]:
        """
        Runs prediction concurrently across all loaded detectors.
        Ensures if one detector fails, it returns an error field but doesn't crash the pipeline.
        """
        results = {}
        for name in list(self.detector_classes.keys()):
            detector = self.get_detector(name)
            if detector:
                try:
                    # Execute prediction safely
                    results[name] = detector.predict(pil_image, **kwargs)
                except Exception as e:
                    results[name] = {
                        "detector": name,
                        "score": 0.0,
                        "confidence": 0.0,
                        "execution_time": 0.0,
                        "error": f"Execution panic: {str(e)}"
                    }
            else:
                results[name] = {
                    "detector": name,
                    "score": 0.0,
                    "confidence": 0.0,
                    "execution_time": 0.0,
                    "error": "Detector not available (failed to load)"
                }
        return results

    def reload_detector(self, name: str) -> bool:
        """
        Hot-reloads a single detector. Useful for configuration updates
        or model file updates without restarting the application.
        """
        if name not in self.detector_classes:
            return False
            
        print(f"[REGISTRY] Hot reloading detector: {name}")
        try:
            # Re-instantiate and load
            cls = self.detector_classes[name]
            
            # If the class was imported from a file, we reload the module first
            module_name = cls.__module__
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
                # Resolve the updated class
                updated_cls = getattr(sys.modules[module_name], cls.__name__)
                self.detector_classes[name] = updated_cls
                cls = updated_cls

            detector_instance = cls()
            success = detector_instance.load()
            
            if success:
                self.detectors[name] = detector_instance
                print(f"[REGISTRY] Hot reload successful for: {name}")
                return True
            else:
                print(f"[REGISTRY] Hot reload failed during initialization for: {name}")
                return False
        except Exception as e:
            print(f"[REGISTRY] Hot reload failed for {name}: {e}")
            return False

# Global registry instance
_global_registry = DetectorRegistry()

def get_registry() -> DetectorRegistry:
    return _global_registry
