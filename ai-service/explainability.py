import os
import cv2
import numpy as np
import base64
import io
from PIL import Image, ImageDraw

# OpenCV fallback
try:
    _face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    HAAR_AVAILABLE = True
except Exception:
    HAAR_AVAILABLE = False

def generate_fft_heatmap(pil_img: Image.Image) -> str:
    """
    Computes FFT magnitude spectrum and colorizes it.
    Returns base64 JPEG string.
    """
    gray = np.array(pil_img.convert("L"), dtype=np.float32)
    f = np.fft.fft2(gray)
    fshift = np.fft.fftshift(f)
    magnitude = 20 * np.log(np.abs(fshift) + 1e-8)
    
    magnitude -= magnitude.min()
    if magnitude.max() > 0:
        magnitude = (magnitude / magnitude.max() * 255).astype(np.uint8)
    else:
        magnitude = np.zeros_like(magnitude, dtype=np.uint8)
        
    color_mapped = cv2.applyColorMap(magnitude, cv2.COLORMAP_JET)
    color_mapped_rgb = cv2.cvtColor(color_mapped, cv2.COLOR_BGR2RGB)
    
    pil_out = Image.fromarray(color_mapped_rgb)
    buffer = io.BytesIO()
    pil_out.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def generate_gan_heatmap(pil_img: Image.Image) -> str:
    """
    Isolates residual noise and colorizes it as a heatmap.
    Returns base64 JPEG string.
    """
    img_arr = np.array(pil_img.convert("RGB"), dtype=np.float32)
    smooth = cv2.GaussianBlur(img_arr, (5, 5), 0)
    residual = np.abs(img_arr - smooth)
    
    norm_res = (residual - residual.min()) / (residual.max() - residual.min() + 1e-6) * 255.0
    norm_res = norm_res.astype(np.uint8)
    
    gray_res = np.mean(norm_res, axis=2).astype(np.uint8)
    
    color_mapped = cv2.applyColorMap(gray_res, cv2.COLORMAP_HOT)
    color_mapped_rgb = cv2.cvtColor(color_mapped, cv2.COLOR_BGR2RGB)
    
    pil_out = Image.fromarray(color_mapped_rgb)
    buffer = io.BytesIO()
    pil_out.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def generate_face_box_overlay(pil_img: Image.Image) -> str:
    """
    Detects face box using Haar Cascades and overlays a green bounding box.
    Returns base64 JPEG string.
    """
    img_cv = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    faces = []
    if HAAR_AVAILABLE:
        faces = _face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        
    out_pil = pil_img.copy()
    draw = ImageDraw.Draw(out_pil)
    
    for (x, y, w, h) in faces:
        draw.rectangle([x, y, x + w, y + h], outline="#00ff00", width=4)
        
    buffer = io.BytesIO()
    out_pil.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def generate_forensic_explanation(scores: dict, final_prob: float) -> dict:
    """
    Translates raw ensemble model scores into a human-readable explanation structure.
    """
    is_fake = final_prob > 0.5
    verdict = "AI_GENERATED" if is_fake else "REAL"
    
    reasons = []
    # 3. EfficientNet / Xception
    eff_val = scores.get("efficientnet", 0.0)
    xcep_val = scores.get("xception", 0.0)
    if eff_val > 0.6 or xcep_val > 0.6:
        reasons.append("Deep CNN classifiers (EfficientNet/XceptionNet) flag localized blending boundaries on face crops.")
    elif eff_val < 0.3 and xcep_val < 0.3:
        reasons.append("CNN facial analysis suggests high texture and lighting consistency across facial boundaries.")

    # 4. Frequency
    freq_val = scores.get("frequency", 0.0)
    if freq_val > 0.5:
        reasons.append("Frequency-domain analysis detected repeating grid/checkerboard upsampling artifacts (FFT/DCT).")

    # 5. Reverse SynthID
    synthid_val = scores.get("synthid", False)
    if synthid_val:
        reasons.append("Reverse SynthID identified constant phase-coherent signals indicating an embedded DeepMind digital watermark.")

    # 6. Metadata
    metadata_val = scores.get("metadata", 0.0)
    if metadata_val > 0.5:
        reasons.append("EXIF metadata audit flagged anomalies: missing camera tags or presence of editing software signatures.")

    # C2PA Content Credentials
    c2pa_detected = scores.get("c2pa_detected", False)
    if c2pa_detected:
        c2pa_valid = scores.get("c2pa_valid", False)
        if c2pa_valid:
            reasons.append("Cryptographically verified Content Credentials (C2PA) are present and valid.")
        else:
            reasons.append("Cryptographically signed Content Credentials (C2PA) are present but invalid or tampered.")


    # 7. Video Temporal (if present)
    temporal_val = scores.get("temporal", None)
    if temporal_val is not None:
        if temporal_val > 0.5:
            reasons.append(f"Temporal consistency check failed: significant inter-frame motion jitter and identity drift.")
        else:
            reasons.append("Temporal consistency analysis shows stable motion continuity and identity alignment across video frames.")

    # 8. Grad-CAM Suspicious Check
    gradcam_suspicious = scores.get("gradcam_suspicious", False)
    if gradcam_suspicious:
        reasons.append("Grad-CAM heatmap highlights highly localized visual anomalies (warm red/orange regions) suggesting blending or generative tampering.")

    summary = f"The media was classified as {'Fake' if is_fake else 'Real'} because:"
    
    return {
        "verdict": verdict,
        "summary": summary,
        "reasons": reasons
    }

