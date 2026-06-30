import numpy as np
import cv2
import scipy.fftpack as fftpack
from PIL import Image, ImageFilter
from detectors.base import BaseDetector

class FrequencyForensics(BaseDetector):
    """
    Combines 5 frequency and statistical artifact detectors:
    1. FFT (Fast Fourier Transform) check
    2. DCT (Discrete Cosine Transform) check
    3. Wavelet analysis (Haar Wavelet decomposition)
    4. Noise Residual kurtosis check
    5. JPEG blockiness analysis
    """
    def _load_model(self) -> bool:
        return True

    def _compute_fft_score(self, gray: np.ndarray) -> float:
        """
        Computes the high-to-low ratio of FFT magnitude spectrum.
        GAN/diffusion models show periodic upsampling patterns in HF bands.
        """
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        magnitude = np.abs(fshift)
        
        h, w = magnitude.shape
        cy, cx = h // 2, w // 2
        
        # Calculate low vs high frequency energy
        y, x = np.ogrid[:h, :w]
        dist = np.sqrt((y - cy)**2 + (x - cx)**2)
        max_dist = min(cy, cx)
        
        low_mask = dist < (max_dist / 8)
        high_mask = (dist > (max_dist / 4)) & (dist < max_dist)
        
        low_energy = np.mean(magnitude[low_mask]) if np.any(low_mask) else 1e-6
        high_energy = np.mean(magnitude[high_mask]) if np.any(high_mask) else 0.0
        
        ratio = high_energy / (low_energy + 1e-8)
        # Normalize: ratio typically ranges from 0.02 (real) to 0.35+ (fake)
        score = min(1.0, max(0.0, (ratio - 0.04) / 0.28))
        return float(score)

    def _compute_dct_score(self, gray: np.ndarray) -> float:
        """
        Computes 2D Discrete Cosine Transform.
        Checks for checkerboard grids by looking at periodic peaks in high-frequency DCT bins.
        """
        # Resize to 256x256 for standard grid size
        small_gray = cv2.resize(gray, (256, 256))
        dct = fftpack.dctn(small_gray, norm='ortho')
        
        # Extract the high-frequency portion (bottom-right triangle of the DCT matrix)
        hf_dct = np.abs(dct[128:, 128:])
        mean_hf = np.mean(hf_dct)
        max_hf = np.max(hf_dct)
        
        # High ratio of peak-to-mean in HF indicates artificial periodicity
        peak_ratio = max_hf / (mean_hf + 1e-6)
        score = min(1.0, max(0.0, (peak_ratio - 4.0) / 12.0))
        return float(score)

    def _compute_wavelet_score(self, gray: np.ndarray) -> float:
        """
        Performs 1-level 2D Haar Wavelet decomposition using pure NumPy.
        Returns the energy distribution check of the high-frequency subbands (LH, HL, HH).
        """
        # Haar Wavelet filters: average/difference of adjacent pixels
        # Top-left (LL), Top-right (HL), Bottom-left (LH), Bottom-right (HH)
        h, w = gray.shape
        # Crop to even dimensions
        h_even = h - (h % 2)
        w_even = w - (w % 2)
        # Cast to float32 to prevent overflow/underflow in uint8 math
        img = gray[:h_even, :w_even].astype(np.float32)
        
        # Compute horizontal averages and differences
        left = img[:, 0::2]
        right = img[:, 1::2]
        
        h_avg = (left + right) / 2.0
        h_diff = (left - right) / 2.0
        
        # Compute vertical averages and differences
        ll = (h_avg[0::2, :] + h_avg[1::2, :]) / 2.0
        lh = (h_avg[0::2, :] - h_avg[1::2, :]) / 2.0
        hl = (h_diff[0::2, :] + h_diff[1::2, :]) / 2.0
        hh = (h_diff[0::2, :] - h_diff[1::2, :]) / 2.0
        
        # Standard images exhibit exponential decay in wavelet subband energy.
        # AI images often have anomalies or grid leakage in HH (high-high diagonal) energy.
        ll_energy = np.mean(ll**2) + 1e-6
        hh_energy = np.mean(hh**2)
        lh_energy = np.mean(lh**2)
        hl_energy = np.mean(hl**2)
        
        ratio = hh_energy / (ll_energy + 1e-8)
        # Normalize: ratio typically ranges from 0.0005 (real) to 0.012+ (fake)
        score = min(1.0, max(0.0, (ratio - 0.0008) / 0.01))
        return float(score)
 
    def _compute_noise_score(self, pil_image: Image.Image) -> float:
        """
        Calculates noise residual kurtosis.
        GAN/Diffusion outputs display highly non-Gaussian peaky distributions (kurtosis >> 3).
        """
        img_arr = np.array(pil_image.resize((256, 256)).convert("RGB"), dtype=np.float32)
        # Apply Gaussian blur
        smooth = cv2.GaussianBlur(img_arr, (5, 5), 0)
        residual = img_arr - smooth
        
        flat = residual.flatten()
        mean = np.mean(flat)
        std = np.std(flat)
        
        if std > 0:
            kurtosis = float(np.mean(((flat - mean) / std) ** 4))
        else:
            kurtosis = 0.0
            
        # Scale: Raise floor to 28.0 to avoid false positives on natural high-frequency edges
        score = min(1.0, max(0.0, (kurtosis - 28.0) / 10.0))
        return float(score)

    def _compute_jpeg_score(self, gray: np.ndarray) -> float:
        """
        Estimate JPEG compression blockiness on an 8x8 grid.
        Calculates differences across block boundaries vs within blocks.
        """
        h, w = gray.shape
        if h < 16 or w < 16:
            return 0.0
            
        # Horizontal differences
        diff_h = np.abs(gray[:, 1:] - gray[:, :-1])
        # Vertical differences
        diff_v = np.abs(gray[1:, :] - gray[:-1, :])
        
        # Block boundaries (multiples of 8)
        block_diff_h = np.mean(diff_h[:, 7::8])
        other_diff_h = np.mean(diff_h[:, [i for i in range(diff_h.shape[1]) if i % 8 != 7]])
        
        block_diff_v = np.mean(diff_v[7::8, :])
        other_diff_v = np.mean(diff_v[[i for i in range(diff_v.shape[0]) if i % 8 != 7], :])
        
        blockiness = (block_diff_h + block_diff_v) / (other_diff_h + other_diff_v + 1e-6)
        
        # Scale: Standard clean photo ~ 1.0; low-quality or heavily re-saved fake ~ 1.2+
        score = min(1.0, max(0.0, (blockiness - 0.95) / 0.4))
        return float(score)

    def _predict(self, pil_image: Image.Image, **kwargs) -> dict:
        img_resized = pil_image.resize((512, 512)).convert("L")
        gray = np.array(img_resized)
        
        fft_s = self._compute_fft_score(gray)
        dct_s = self._compute_dct_score(gray)
        wavelet_s = self._compute_wavelet_score(gray)
        noise_s = self._compute_noise_score(pil_image)
        jpeg_s = self._compute_jpeg_score(gray)
        
        # Combine the forensics scores
        # JPEG score is weighted lower since real compressed photos can also have blockiness.
        # FFT, DCT, Wavelet, and Noise residuals carry the core GAN/Diffusion forensics signals.
        combined_score = (fft_s * 0.25) + (dct_s * 0.25) + (wavelet_s * 0.20) + (noise_s * 0.20) + (jpeg_s * 0.10)
        
        return {
            "score": combined_score,
            "confidence": abs(combined_score - 0.5) * 2,
            "details": {
                "fft_score": round(fft_s, 4),
                "dct_score": round(dct_s, 4),
                "wavelet_score": round(wavelet_s, 4),
                "noise_score": round(noise_s, 4),
                "jpeg_score": round(jpeg_s, 4)
            }
        }
