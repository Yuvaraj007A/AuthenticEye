import time
from PIL import Image

class BaseDetector:
    """
    Abstract base class for all deepfake and AI content detectors.
    Every detector class must inherit from this and implement the predict method.
    """
    def __init__(self):
        self.is_loaded = False
        self.load_error = None

    def load(self) -> bool:
        """
        Load the model weights/checkpoints.
        Should return True if loaded successfully, False otherwise.
        """
        try:
            success = self._load_model()
            self.is_loaded = success
            return success
        except Exception as e:
            self.is_loaded = False
            self.load_error = str(e)
            print(f"[ERROR] Failed to load detector {self.__class__.__name__}: {e}")
            return False

    def _load_model(self) -> bool:
        """Override in subclasses to perform actual loading."""
        return True

    def predict(self, pil_image: Image.Image, **kwargs) -> dict:
        """
        Executes inference on a PIL image.
        Returns a standardized output:
        {
            "detector": "NameOfDetector",
            "score": float (probability of AI/Fake, 0.0 to 1.0),
            "confidence": float (confidence of prediction, 0.0 to 1.0),
            "execution_time": float (seconds taken)
        }
        """
        if not self.is_loaded:
            # Try loading if not loaded yet
            if not self.load():
                return {
                    "detector": self.__class__.__name__,
                    "score": 0.0,
                    "confidence": 0.0,
                    "execution_time": 0.0,
                    "error": self.load_error or "Not loaded"
                }

        start_time = time.time()
        try:
            result = self._predict(pil_image, **kwargs)
            exec_time = time.time() - start_time
            
            # Formulate confidence (distance from decision boundary of 0.5)
            score = float(result.get("score", 0.5))
            confidence = float(result.get("confidence", abs(score - 0.5) * 2))
            
            return {
                "detector": self.__class__.__name__,
                "score": round(score, 4),
                "confidence": round(confidence, 4),
                "execution_time": round(exec_time, 4),
                "details": result.get("details", {})
            }
        except Exception as e:
            exec_time = time.time() - start_time
            print(f"[ERROR] Predict failed in {self.__class__.__name__}: {e}")
            return {
                "detector": self.__class__.__name__,
                "score": 0.0,
                "confidence": 0.0,
                "execution_time": round(exec_time, 4),
                "error": str(e)
            }

    def _predict(self, pil_image: Image.Image, **kwargs) -> dict:
        """Override in subclasses to perform model inference."""
        raise NotImplementedError("Subclasses must implement _predict")
