import numpy as np
import cv2
from scipy.fft import rfft2
from PIL import Image
from detectors.base import BaseDetector

class SynthIDDetector(BaseDetector):
    """
    SynthID Watermark Detector using FFT spectral analysis.
    No pre-built codebook required.
    """
    def _load_model(self) -> bool:
        return True

    def _predict(self, pil_image: Image.Image, **kwargs) -> dict:
        h, w = pil_image.height, pil_image.width
        
        # Convert PIL Image to gray numpy array
        img_np = np.array(pil_image)
        if len(img_np.shape) == 3:
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY).astype(np.float32)
        else:
            gray = img_np.astype(np.float32)
            
        # Compute FFT
        fft_result = rfft2(gray)
        magnitude = np.abs(fft_result)
        
        # Scale SynthID carrier frequencies to current resolution
        scale_y = h / 1024.0
        scale_x = w / 1024.0
        
        # Check for diagonal carrier pattern (±14, ±14)
        primary_carriers = [
            (int(14 * scale_y), int(14 * scale_x)),
            (int(14 * scale_y), int(-14 * scale_x) % w),
            (int(98 * scale_y), int(14 * scale_x)),
            (int(98 * scale_y), int(-14 * scale_x) % w),
        ]
        
        # Localized peak detection: compare each carrier's magnitude to its local 11x11 neighborhood
        peak_ratios = []
        carrier_energies = []
        for y, x in primary_carriers:
            y = max(0, min(y, magnitude.shape[0] - 1))
            x = max(0, min(x, magnitude.shape[1] - 1))
            
            carrier_val = magnitude[y, x]
            carrier_energies.append(carrier_val)
            
            # Local 11x11 neighborhood
            y_start = max(0, y - 5)
            y_end = min(magnitude.shape[0], y + 6)
            x_start = max(0, x - 5)
            x_end = min(magnitude.shape[1], x + 6)
            
            local_region = magnitude[y_start:y_end, x_start:x_end]
            local_mask = np.ones_like(local_region, dtype=bool)
            cy, cx = y - y_start, x - x_start
            
            # Exclude a 3x3 region around the carrier center
            local_mask[max(0, cy - 1):min(local_region.shape[0], cy + 2), 
                       max(0, cx - 1):min(local_region.shape[1], cx + 2)] = False
                       
            local_bg = np.mean(local_region[local_mask]) if np.any(local_mask) else 1.0
            ratio = carrier_val / max(local_bg, 1.0)
            peak_ratios.append(ratio)
            
        avg_carrier = np.mean(carrier_energies) if carrier_energies else 0.0
        carrier_ratio = float(np.mean(peak_ratios)) if peak_ratios else 0.0
        
        # Background energy (away from DC and carriers) - kept for compatibility of details
        bg_mask = np.ones_like(magnitude, dtype=bool)
        for y, x in primary_carriers:
            y = max(0, min(y, magnitude.shape[0] - 1))
            x = max(0, min(x, magnitude.shape[1] - 1))
            y_start = max(0, y - 5)
            y_end = min(magnitude.shape[0], y + 6)
            x_start = max(0, x - 5)
            x_end = min(magnitude.shape[1], x + 6)
            bg_mask[y_start:y_end, x_start:x_end] = False
        
        bg_mask[0, 0] = False # Exclude DC component
        bg_energy = np.mean(magnitude[bg_mask]) if np.any(bg_mask) else 1.0
        
        # Compute metrics
        dc_energy = float(magnitude[0, 0])
        avg_energy = float(np.mean(magnitude))
        
        # Spectral sparsity (SynthID has specific frequency structure)
        energy_concentration = float(np.sum(magnitude[magnitude > np.percentile(magnitude, 95)]) / np.sum(magnitude))
        
        # SynthID detection heuristic
        # A true watermark peak should stand out significantly from its local neighborhood
        carrier_threshold = 4.0
        concentration_threshold = 0.25
        
        is_watermarked = (carrier_ratio > carrier_threshold and 
                          energy_concentration > concentration_threshold)
        
        confidence = float(min(carrier_ratio / carrier_threshold * 0.6 +
                        energy_concentration / concentration_threshold * 0.4, 1.0))
                        
        # Map score to [0.0, 1.0] matching threshold bounds
        if is_watermarked:
            score = carrier_ratio / (carrier_ratio + 1.0)
            score = max(0.51, score)
        else:
            # Scale score so that it is close to 0.0 if not detected
            score = (carrier_ratio / carrier_threshold) * 0.15
            score = min(0.49, max(0.0, score))
            
        return {
            "score": round(score, 4),
            "confidence": round(confidence, 4),
            "details": {
                "synthid_detected": bool(is_watermarked),
                "carrier_ratio": round(carrier_ratio, 4),
                "energy_concentration": round(energy_concentration, 4),
                "dc_energy": round(dc_energy, 2),
                "avg_energy": round(avg_energy, 2),
                "carrier_energy": round(float(avg_carrier), 2),
                "background_energy": round(float(bg_energy), 2)
            }
        }
