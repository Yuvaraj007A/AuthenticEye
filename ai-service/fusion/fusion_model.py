import torch
import torch.nn as nn

class AuthenticEyeFusionMLP(nn.Module):
    """
    Meta-classifier that fuses all deep CNN logits and statistical/CLIP features.
    
    Expected Feature Vector Size: 16
    - Image Model Logits: 3 (EfficientNet, Xception, ViT)
    - FFT Features: 3 (hf_energy, lf_energy, ratio)
    - GAN Features: 3 (kurtosis, noise_energy, cross_corr)
    - Diffusion Features: 3 (color_coherence, edge_sharpness, isotropy)
    - CLIP Features: 4 (cosine similarities to prompt anchors)
    """
    
    def __init__(self, input_dim=16, hidden_1=256, hidden_2=128):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_1),
            nn.BatchNorm1d(hidden_1),
            nn.ReLU(),
            nn.Dropout(0.3),
            
            nn.Linear(hidden_1, hidden_2),
            nn.BatchNorm1d(hidden_2),
            nn.ReLU(),
            nn.Dropout(0.3),
            
            nn.Linear(hidden_2, 1) # Output single logit
        )

    def forward(self, x):
        return self.network(x)
