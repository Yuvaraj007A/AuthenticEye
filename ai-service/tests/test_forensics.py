import os
import sys
import unittest
import numpy as np
from PIL import Image

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from detectors.frequency_forensics import FrequencyForensics
from detectors.synthid import SynthIDDetector
from detectors.metadata_analyzer import MetadataAnalyzer

class TestForensics(unittest.TestCase):
    def setUp(self):
        self.freq_forensics = FrequencyForensics()
        self.freq_forensics.load()
        
        self.synthid_detector = SynthIDDetector()
        self.synthid_detector.load()
        
        self.metadata_analyzer = MetadataAnalyzer()
        self.metadata_analyzer.load()

    def test_frequency_forensics_run(self):
        # Create solid color image
        img = Image.new("RGB", (256, 256), color="blue")
        res = self.freq_forensics.predict(img)
        
        self.assertIn("score", res)
        self.assertIn("fft_score", res["details"])
        self.assertIn("dct_score", res["details"])
        self.assertIn("wavelet_score", res["details"])
        self.assertIn("noise_score", res["details"])
        self.assertIn("jpeg_score", res["details"])

    def test_synthid_watermark_run(self):
        img = Image.new("RGB", (256, 256), color="white")
        res = self.synthid_detector.predict(img)
        
        self.assertIn("score", res)
        self.assertIn("carrier_ratio", res["details"])
        self.assertIn("energy_concentration", res["details"])
        self.assertIn("synthid_detected", res["details"])

    def test_metadata_risk_run(self):
        img = Image.new("RGB", (100, 100), color="green")
        res = self.metadata_analyzer.predict(img)
        
        self.assertIn("score", res)
        # Without real EXIF header, the risk score should be computed
        self.assertGreater(res["score"], 0.0)

    def test_gradcam_run(self):
        from detectors.efficientnet_dfdc import EfficientNetDFDC
        from preprocessing import preprocess_image_for_ensemble
        from gradcam import generate_gradcam_heatmap
        
        eff = EfficientNetDFDC()
        eff.load()
        
        img = Image.new("RGB", (224, 224), color="blue")
        tensor, _ = preprocess_image_for_ensemble(img)
        
        heatmap_b64, _ = generate_gradcam_heatmap(eff, tensor, img)
        # Verify it succeeds and doesn't return empty string
        self.assertNotEqual(heatmap_b64, "")
        self.assertTrue(heatmap_b64.startswith("/9j/")) # Base64 for JPEG starts with /9j/ or is not empty

if __name__ == "__main__":
    unittest.main()
