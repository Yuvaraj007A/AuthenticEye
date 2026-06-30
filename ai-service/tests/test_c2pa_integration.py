import os
import sys
import unittest
import requests
from PIL import Image
import io

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from detectors.registry import get_registry

class TestC2PAIntegration(unittest.TestCase):
    def test_firefly_ai_signed_image(self):
        url = "https://contentauth.github.io/example-assets/images/Firefly_tabby_cat.jpg"
        print(f"\nDownloading Adobe Firefly signed AI image: {url}")
        
        try:
            response = requests.get(url, timeout=15)
            if response.status_code != 200:
                self.skipTest(f"Failed to download image (status code: {response.status_code}).")
        except Exception as e:
            self.skipTest(f"Skipping test: network error ({e}).")
            
        file_bytes = response.content
        pil_image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        
        registry = get_registry()
        detector = registry.get_detector("C2PADetector")
        self.assertIsNotNone(detector)
        
        res = detector.predict(pil_image, file_bytes=file_bytes, mime_type="image/jpeg")
        print("\nAdobe Firefly Prediction result details:")
        import pprint
        pprint.pprint(res)
        
        self.assertTrue(res["details"]["c2pa_detected"], "C2PA manifest should be detected")
        self.assertTrue(res["details"]["c2pa_valid"], "C2PA signature should be valid")
        self.assertTrue(res["details"]["is_ai_generated"], "Should be identified as AI-generated")
        self.assertEqual(res["score"], 1.0)

    def test_standard_signed_image(self):
        url = "https://contentauth.github.io/example-assets/images/car-es-Ps-Cr.jpg"
        print(f"\nDownloading standard signed image: {url}")
        
        try:
            response = requests.get(url, timeout=15)
            if response.status_code != 200:
                self.skipTest(f"Failed to download image (status code: {response.status_code}).")
        except Exception as e:
            self.skipTest(f"Skipping test: network error ({e}).")
            
        file_bytes = response.content
        pil_image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        
        registry = get_registry()
        detector = registry.get_detector("C2PADetector")
        
        res = detector.predict(pil_image, file_bytes=file_bytes, mime_type="image/jpeg")
        print("\nStandard Signed Image Prediction result details:")
        import pprint
        pprint.pprint(res)
        
        self.assertTrue(res["details"]["c2pa_detected"], "C2PA manifest should be detected")
        self.assertTrue(res["details"]["c2pa_valid"], "C2PA signature should be valid")
        # Since it's a camera/editor and not AI generator, is_ai_generated should be False or we assess the score
        self.assertEqual(res["score"], 0.0)

if __name__ == "__main__":
    unittest.main()
