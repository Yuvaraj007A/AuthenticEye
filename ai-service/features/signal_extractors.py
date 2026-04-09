import numpy as np
import cv2
from PIL import Image

class FFTExtractor:
    """Extracts frequency domain features via FFT."""
    
    def extract(self, pil_img: Image.Image) -> list[float]:
        """Returns [high_freq_energy, low_freq_energy, hf_lf_ratio]"""
        gray = pil_img.convert("L")
        img_arr = np.array(gray, dtype=np.float32)
        
        f = np.fft.fft2(img_arr)
        fshift = np.fft.fftshift(f)
        magnitude_spectrum = np.abs(fshift)
        
        rows, cols = img_arr.shape
        crow, ccol = rows // 2, cols // 2
        r = 30 # low frequency radius
        
        # Mask for low frequencies
        mask = np.zeros((rows, cols), np.uint8)
        cv2.circle(mask, (ccol, crow), r, 1, thickness=-1)
        
        low_freq_energy = np.sum(magnitude_spectrum * mask)
        high_freq_energy = np.sum(magnitude_spectrum * (1 - mask))
        
        lf_energy_norm = float(low_freq_energy / (rows * cols))
        hf_energy_norm = float(high_freq_energy / (rows * cols))
        
        ratio = hf_energy_norm / (lf_energy_norm + 1e-6)
        
        return [hf_energy_norm, lf_energy_norm, ratio]


class GANFingerprintExtractor:
    """Extracts GAN noise statistic features."""
    
    def __init__(self):
        self._hp_kernel = np.array([
            [-1, -1, -1],
            [-1,  8, -1],
            [-1, -1, -1],
        ], dtype=np.float32) / 8.0

    def extract(self, pil_img: Image.Image) -> list[float]:
        """Returns [kurtosis, noise_energy, cross_channel_corr]"""
        img_arr = np.array(pil_img.convert("RGB"), dtype=np.float32)
        
        noise_channels = []
        for c in range(3):
            channel = img_arr[:, :, c]
            smooth = cv2.GaussianBlur(channel, (5, 5), 0)
            residual = channel - smooth
            hp = cv2.filter2D(residual, -1, self._hp_kernel)
            noise_channels.append(hp)
            
        noise_map = np.stack(noise_channels, axis=2)
        
        # Statistics
        flat = noise_map.flatten()
        mean = np.mean(flat)
        std = np.std(flat)
        
        kurtosis = float(np.mean(((flat - mean) / (std + 1e-6)) ** 4)) if std > 0 else 0.0
        noise_energy = float(np.mean(noise_map ** 2))
        
        r = noise_map[:, :, 0].flatten()
        g = noise_map[:, :, 1].flatten()
        b = noise_map[:, :, 2].flatten()
        
        corr_rg = float(np.corrcoef(r, g)[0, 1]) if np.std(r) > 0 and np.std(g) > 0 else 0.0
        corr_rb = float(np.corrcoef(r, b)[0, 1]) if np.std(r) > 0 and np.std(b) > 0 else 0.0
        cross_corr = (abs(corr_rg) + abs(corr_rb)) / 2.0
        
        return [kurtosis, noise_energy, cross_corr]

class DiffusionExtractor:
    """Extracts Diffusion-specific features."""
    
    def extract(self, pil_img: Image.Image) -> list[float]:
        """Returns [color_coherence, edge_sharpness, isotropy]"""
        img_arr = np.array(pil_img.convert("RGB"))
        
        # Very simplified pseudo-metrics for color coherence and edge sharpness
        # Real diffusion detectors look at color palette size, sharpness std dev.
        
        hsv = cv2.cvtColor(img_arr, cv2.COLOR_RGB2HSV)
        color_coherence = float(np.std(hsv[:, :, 0])) # Hue std deviation
        
        gray = cv2.cvtColor(img_arr, cv2.COLOR_RGB2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        edge_sharpness = float(np.var(laplacian))
        
        # Gradient isotropy
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        mag = np.sqrt(gx**2 + gy**2)
        dir = np.arctan2(gy, gx)
        hist, _ = np.histogram(dir, bins=8, range=(-np.pi, np.pi))
        isotropy = float(np.std(hist) / (np.mean(hist) + 1e-6))
        
        return [color_coherence, edge_sharpness, isotropy]
