import torch
import torch.nn as nn
import timm

class EfficientNetDetector(nn.Module):
    """EfficientNet-B4 fine-tuned as binary classifier (logits)."""
    def __init__(self, pretrained=True):
        super().__init__()
        self.base = timm.create_model("efficientnet_b4", pretrained=pretrained, num_classes=1)

    def forward(self, x):
        # Return logits instead of sigmoid
        return self.base(x)

class XceptionDetector(nn.Module):
    """Xception model as binary classifier (logits)."""
    def __init__(self, pretrained=True):
        super().__init__()
        self.base = timm.create_model("xception", pretrained=pretrained, num_classes=1)

    def forward(self, x):
        return self.base(x)

class ViTDetector(nn.Module):
    """Vision Transformer (ViT-B/16) as binary classifier (logits)."""
    def __init__(self, pretrained=True):
        super().__init__()
        self.base = timm.create_model("vit_base_patch16_224", pretrained=pretrained, num_classes=1)

    def forward(self, x):
        return self.base(x)
