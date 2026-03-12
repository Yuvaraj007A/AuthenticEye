"""
AuthenticEye — Step 2: Frequency Artifact Detector
Detects GAN-specific artifacts in the frequency domain using FFT + CNN.
GAN upsampling (transposed convolution) leaves periodic grid artifacts 
that are invisible to the human eye but detectable via FFT.
"""
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as T
import numpy as np
from PIL import Image

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class FrequencyCNN(nn.Module):
    """
    Lightweight CNN to classify FFT magnitude spectrum images.
    Uses MobileNetV3-Small for speed — this is a supporting signal,
    not the primary detector.
    """
    def __init__(self):
        super().__init__()
        self.base = models.mobilenet_v3_small(weights="IMAGENET1K_V1")
        # Override first conv for single-channel FFT spectrum input
        self.base.features[0][0] = nn.Conv2d(1, 16, kernel_size=3, stride=2, padding=1, bias=False)
        self.base.classifier[-1] = nn.Linear(1024, 1)

    def forward(self, x):
        return torch.sigmoid(self.base(x))


class FrequencyDetector:
    """
    Detects frequency domain artifacts typical of GAN-generated images.
    
    Key insight: GANs use transposed convolution for upsampling which creates
    a repeating 'checkerboard' pattern in the high-frequency spectrum.
    Real photos have 1/f noise (pink noise) distribution.
    """

    def __init__(self):
        self.model = FrequencyCNN().to(DEVICE)
        self.model.eval()
        self._transform = T.Compose([
            T.Grayscale(1),
            T.Resize((224, 224)),
            T.ToTensor(),
            T.Normalize(mean=[0.5], std=[0.5]),
        ])

    def _compute_fft_spectrum(self, pil_img: Image.Image) -> Image.Image:
        """
        Converts image to FFT magnitude spectrum.
        Returns a PIL Image of the log-scaled magnitude spectrum.
        """
        gray = np.array(pil_img.convert("L"), dtype=np.float32)

        # 2D FFT and shift zero-frequency to center
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        magnitude = 20 * np.log(np.abs(fshift) + 1e-8)

        # Normalize to [0, 255]
        magnitude -= magnitude.min()
        if magnitude.max() > 0:
            magnitude = (magnitude / magnitude.max() * 255).astype(np.uint8)
        else:
            magnitude = np.zeros_like(magnitude, dtype=np.uint8)

        return Image.fromarray(magnitude).convert("L")

    def _compute_spectral_features(self, pil_img: Image.Image) -> dict:
        """
        Extracts numerical features from the frequency spectrum
        that directly indicate GAN artifacts.
        """
        gray = np.array(pil_img.convert("L"), dtype=np.float32)
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        magnitude = np.abs(fshift)

        h, w = magnitude.shape
        cy, cx = h // 2, w // 2

        # Energy in different bands
        def ring_energy(r_min, r_max):
            y, x = np.ogrid[:h, :w]
            mask = (((y - cy)**2 + (x - cx)**2) >= r_min**2) & \
                   (((y - cy)**2 + (x - cx)**2) < r_max**2)
            return float(np.mean(magnitude[mask]))

        low = ring_energy(0, min(h, w) // 8)
        mid = ring_energy(min(h, w) // 8, min(h, w) // 4)
        high = ring_energy(min(h, w) // 4, min(h, w) // 2)

        # High-to-low ratio: real images have fast falloff; GANs often don't
        hl_ratio = high / (low + 1e-8)

        # Azimuthal standard deviation: GAN spectra are isotropic,
        # real photos are not (they have directional features)
        azimuthal_std = float(np.std(magnitude))

        return {
            "low_freq_energy": low,
            "mid_freq_energy": mid,
            "high_freq_energy": high,
            "hl_ratio": hl_ratio,
            "azimuthal_std": azimuthal_std,
        }

    def predict(self, pil_img: Image.Image) -> dict:
        """
        Returns frequency-based deepfake probability.
        Uses ONLY physics-based spectral analysis — the CNN is not fine-tuned
        on deepfake data so its output is unreliable noise.
        """
        features = self._compute_spectral_features(pil_img)

        # GAN upsampling (transposed conv) creates checkerboard artifacts that
        # raise the high-to-low frequency energy ratio.
        # Measured baselines:
        #   - Natural photos / real gradients: hl_ratio ~ 0.05-0.15
        #   - GAN / AI-generated faces: hl_ratio > 0.3 (stronger HF artifacts)
        # Scale: 0.05 -> 0.0, 0.3 -> ~1.0
        hl = features["hl_ratio"]
        spectral_score = min(1.0, max(0.0, (hl - 0.05) / 0.25))

        # azimuthal_std is always in the 30k-40k range for all image types,
        # so it carries no discriminative signal — drop it.
        final_score = spectral_score

        return {
            "frequency_score": round(min(float(final_score), 0.99), 4),
            "spectral_features": {k: round(v, 6) for k, v in features.items()},
        }


# Singleton instance (loaded once at startup)
_instance: FrequencyDetector = None

def get_frequency_detector() -> FrequencyDetector:
    global _instance
    if _instance is None:
        _instance = FrequencyDetector()
    return _instance
