import numpy as np
import cv2
from PIL import Image

class ArtifactDetector:
    """
    Detects compression, GAN, and blending artifacts in images.
    """
    def _compute_jpeg_blockiness(self, gray_arr: np.ndarray) -> float:
        """
        Estimate JPEG compression blockiness on an 8x8 grid.
        Calculates differences across block boundaries vs within blocks.
        """
        h, w = gray_arr.shape
        if h < 16 or w < 16:
            return 0.0
        
        # Horizontal differences
        diff_h = np.abs(gray_arr[:, 1:] - gray_arr[:, :-1])
        # Vertical differences
        diff_v = np.abs(gray_arr[1:, :] - gray_arr[:-1, :])
        
        # Block boundaries (multiples of 8)
        block_diff_h = np.mean(diff_h[:, 7::8])
        other_diff_h = np.mean(diff_h[:, [i for i in range(diff_h.shape[1]) if i % 8 != 7]])
        
        block_diff_v = np.mean(diff_v[7::8, :])
        other_diff_v = np.mean(diff_v[[i for i in range(diff_v.shape[0]) if i % 8 != 7], :])
        
        blockiness = (block_diff_h + block_diff_v) / (other_diff_h + other_diff_v + 1e-6)
        # Standard JPEG has blockiness close to 1.0; low-quality or heavily compressed has blockiness > 1.2
        return float(min(1.0, max(0.0, (blockiness - 0.9) / 0.5)))

    def _compute_gan_artifacts(self, pil_img: Image.Image) -> float:
        """
        Estimate GAN artifacts using high-frequency residual noise statistics.
        StyleGAN/CycleGAN leave distinct noise distributions.
        """
        img_arr = np.array(pil_img.convert("RGB"), dtype=np.float32)
        # Extract residual noise (Original - Smoothed)
        smooth = cv2.GaussianBlur(img_arr, (5, 5), 0)
        residual = img_arr - smooth
        
        # Calculate kurtosis of noise distribution (measures peakiness / non-Gaussianity)
        flat = residual.flatten()
        mean = np.mean(flat)
        std = np.std(flat)
        kurtosis = float(np.mean(((flat - mean) / (std + 1e-6)) ** 4)) if std > 0 else 0.0
        
        # Scale: kurtosis of real photos is typically < 5; GAN images often > 8
        gan_score = min(1.0, max(0.0, (kurtosis - 4.5) / 5.5))
        return gan_score

    def _compute_blending_artifacts(self, pil_img: Image.Image) -> float:
        """
        Detect blending artifacts / edge inconsistencies.
        Typically found at spliced image boundaries.
        We estimate edge variance discontinuity by computing local edge variance.
        """
        gray = np.array(pil_img.convert("L"), dtype=np.uint8)
        # Compute Sobel gradients
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        grad_mag = np.sqrt(sobelx**2 + sobely**2)
        
        # High variance in local edge magnitude suggests splicing/blending artifacts
        edge_variance = np.std(grad_mag)
        # Normalize score
        blending_score = float(min(1.0, edge_variance / 150.0))
        return blending_score

    def predict(self, pil_img: Image.Image) -> dict:
        gray_arr = np.array(pil_img.convert("L"), dtype=np.float32)
        
        comp_score = self._compute_jpeg_blockiness(gray_arr)
        gan_score = self._compute_gan_artifacts(pil_img)
        blend_score = self._compute_blending_artifacts(pil_img)
        
        # Max of the three artifact scores representing overall artifact probability
        artifact_prob = max(comp_score, gan_score, blend_score)
        
        return {
            "artifact_probability": round(artifact_prob, 4),
            "compression_artifact": round(comp_score, 4),
            "gan_artifact": round(gan_score, 4),
            "blending_artifact": round(blend_score, 4)
        }
