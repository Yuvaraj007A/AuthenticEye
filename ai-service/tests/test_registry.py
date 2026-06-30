import os
import sys
import unittest
import numpy as np
from PIL import Image

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from detectors.registry import get_registry
from detectors.base import BaseDetector

class DummyDetector(BaseDetector):
    """Mock detector for registry testing."""
    def _load_model(self) -> bool:
        return True

    def _predict(self, pil_image: Image.Image, **kwargs) -> dict:
        return {
            "score": 0.75,
            "confidence": 0.5,
            "details": {"mock": True}
        }

class TestRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = get_registry()
        # Register dummy
        self.registry.register("DummyDetector", DummyDetector)

    def test_registration(self):
        self.assertIn("DummyDetector", self.registry.detector_classes)

    def test_lazy_loading(self):
        detector = self.registry.get_detector("DummyDetector")
        self.assertIsNotNone(detector)
        self.assertTrue(detector.is_loaded)

    def test_prediction(self):
        img = Image.new("RGB", (100, 100), color="red")
        res = self.registry.predict_all(img)
        self.assertIn("DummyDetector", res)
        self.assertEqual(res["DummyDetector"]["score"], 0.75)
        self.assertEqual(res["DummyDetector"]["details"]["mock"], True)

if __name__ == "__main__":
    unittest.main()
