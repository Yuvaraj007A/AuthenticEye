import os
from PIL import Image
from PIL.ExifTags import TAGS
from detectors.base import BaseDetector

class MetadataAnalyzer(BaseDetector):
    """
    Analyzes EXIF records, software signatures, camera tags, compression,
    and PNG text comments to evaluate deepfake / AI-generation metadata risk.
    """
    def _load_model(self) -> bool:
        return True

    def _predict(self, pil_image: Image.Image, **kwargs) -> dict:
        risk_score = 0.0
        details = {
            "exif_found": False,
            "missing_camera_metadata": True,
            "editing_software_detected": False,
            "ai_chunks_detected": False,
            "software_signature": None,
            "found_keys": []
        }
        
        # 1. Check PNG Text Chunks / Pillow Info
        info_keys = pil_image.info.keys()
        details["found_keys"] = list(info_keys)
        
        ai_keywords = ["parameters", "prompt", "stable diffusion", "midjourney", "dall-e", "comfyui", "novelai", "steerable-naive"]
        for key in info_keys:
            val = str(pil_image.info[key]).lower()
            if any(keyword in val or keyword in str(key).lower() for keyword in ai_keywords):
                details["ai_chunks_detected"] = True
                risk_score += 0.85
                
        # 2. Extract EXIF data
        try:
            exif = pil_image.getexif()
            if exif:
                details["exif_found"] = True
                
                # Retrieve named tags
                exif_dict = {}
                for tag_id in exif:
                    tag_name = TAGS.get(tag_id, tag_id)
                    data = exif.get(tag_id)
                    # Convert bytes to string if needed
                    if isinstance(data, bytes):
                        try:
                            data = data.decode("utf-8", errors="ignore")
                        except Exception:
                            pass
                    exif_dict[str(tag_name).lower()] = str(data)
                
                # Check for camera parameters (Make, Model indicate physical origin)
                has_make = "make" in exif_dict
                has_model = "model" in exif_dict
                if has_make and has_model:
                    details["missing_camera_metadata"] = False
                else:
                    # Missing make/model adds mild risk
                    risk_score += 0.25
                    
                # Check for software signatures (indicating GIMP, Photoshop, etc.)
                software = exif_dict.get("software", "")
                if software:
                    details["software_signature"] = software
                    editing_keywords = ["photoshop", "gimp", "adobe", "lightroom", "pixelmator", "stable-diffusion"]
                    if any(kw in software.lower() for kw in editing_keywords):
                        details["editing_software_detected"] = True
                        risk_score += 0.45
            else:
                # No EXIF data at all (common for web images, but also AI images)
                risk_score += 0.35
        except Exception as e:
            print(f"[MetadataAnalyzer] EXIF parse warning: {e}")
            risk_score += 0.30
            
        # Clamp final metadata risk score
        risk_score = min(0.99, max(0.01, risk_score))
        
        return {
            "score": risk_score,
            "confidence": abs(risk_score - 0.5) * 2,
            "details": details
        }
