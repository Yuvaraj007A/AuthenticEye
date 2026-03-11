"""
AuthenticEye — Grad-CAM Explainability Module
Generates heatmaps showing which regions the model focused on.
"""
import torch
import torch.nn.functional as F
import numpy as np
import base64
import io
from PIL import Image


class GradCAM:
    """
    Gradient-weighted Class Activation Mapping for CNN models.
    Hooks into the last convolutional layer.
    """
    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None
        self._register_hooks()

    def _register_hooks(self):
        def forward_hook(module, input, output):
            self.activations = output.detach()

        def backward_hook(module, grad_in, grad_out):
            self.gradients = grad_out[0].detach()

        self.target_layer.register_forward_hook(forward_hook)
        self.target_layer.register_backward_hook(backward_hook)

    def generate(self, input_tensor: torch.Tensor) -> np.ndarray:
        self.model.eval()

        output = self.model(input_tensor)
        self.model.zero_grad()
        output.backward(torch.ones_like(output))

        if self.gradients is None or self.activations is None:
            return None

        pooled_gradients = torch.mean(self.gradients, dim=[0, 2, 3])
        for i in range(self.activations.shape[1]):
            self.activations[:, i, :, :] *= pooled_gradients[i]

        heatmap = torch.mean(self.activations, dim=1).squeeze().cpu().numpy()
        heatmap = np.maximum(heatmap, 0)
        if heatmap.max() > 0:
            heatmap /= heatmap.max()
        return heatmap


def _get_last_conv_layer(model):
    """Traverse the model tree to find the last Conv2d layer."""
    last_conv = None
    for module in model.modules():
        if isinstance(module, torch.nn.Conv2d):
            last_conv = module
    return last_conv


def generate_gradcam_heatmap(ensemble_detector, input_tensor: torch.Tensor, original_pil: Image.Image) -> str:
    """
    Run Grad-CAM on the primary EfficientNet model and return
    a base64-encoded JPEG of the heatmap overlaid on the original image.
    """
    try:
        primary_model = ensemble_detector.get_primary_model()
        target_layer = _get_last_conv_layer(primary_model)

        if target_layer is None:
            return ""

        grad_cam = GradCAM(primary_model, target_layer)
        heatmap = grad_cam.generate(input_tensor.clone().requires_grad_(True))

        if heatmap is None:
            return ""

        # Resize heatmap to original image size
        orig_w, orig_h = original_pil.size
        heatmap_resized = np.uint8(255 * heatmap)
        import cv2
        heatmap_colored = cv2.applyColorMap(
            cv2.resize(heatmap_resized, (orig_w, orig_h)), cv2.COLORMAP_JET
        )
        heatmap_rgb = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)

        # Overlay on original image
        orig_np = np.array(original_pil.resize((orig_w, orig_h)))
        overlay = cv2.addWeighted(orig_np, 0.6, heatmap_rgb, 0.4, 0)

        # Encode to base64 JPEG
        pil_overlay = Image.fromarray(overlay)
        buffer = io.BytesIO()
        pil_overlay.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode("utf-8")

    except Exception as e:
        print(f"Grad-CAM failed: {e}")
        return ""
