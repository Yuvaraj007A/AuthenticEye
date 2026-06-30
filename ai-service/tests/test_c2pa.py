import os
import sys
import unittest
from PIL import Image
import io

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from detectors.registry import get_registry
from detectors.c2pa_detector import C2PADetector

class TestC2PADetector(unittest.TestCase):
    def setUp(self):
        self.registry = get_registry()

    def test_registration(self):
        self.assertIn("C2PADetector", self.registry.detector_classes)

    def test_lazy_loading(self):
        detector = self.registry.get_detector("C2PADetector")
        self.assertIsNotNone(detector)
        self.assertTrue(detector.is_loaded)

    def test_prediction_without_bytes(self):
        detector = self.registry.get_detector("C2PADetector")
        img = Image.new("RGB", (100, 100), color="blue")
        res = detector.predict(img)
        
        self.assertEqual(res["score"], 0.0)
        self.assertEqual(res["confidence"], 0.0)
        self.assertIn("Original file bytes were not provided", res["details"]["error"])

    def test_prediction_with_valid_image_no_c2pa(self):
        detector = self.registry.get_detector("C2PADetector")
        img = Image.new("RGB", (100, 100), color="green")
        
        # Export valid JPEG image to bytes
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        jpeg_bytes = buffer.getvalue()
        
        res = detector.predict(img, file_bytes=jpeg_bytes, mime_type="image/jpeg")
        
        self.assertEqual(res["score"], 0.0)
        self.assertEqual(res["confidence"], 0.0)
        self.assertIn("No C2PA manifest found", res["details"]["error"])

if __name__ == "__main__":
    unittest.main()
