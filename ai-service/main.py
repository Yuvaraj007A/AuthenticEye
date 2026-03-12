"""
AuthenticEye AI Service v5.0 — Production Entrypoint
Advanced Research-Grade Deepfake Detection
Removes audio detection, adds frequency, GAN fingerprint, diffusion, temporal analysis
"""
import os
import io
import asyncio
import torch
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from dotenv import load_dotenv

from model import EnsembleImageDetector, load_models
from temporal_detector import TemporalVideoDetector
from preprocessing import preprocess_image_for_ensemble
from gradcam import generate_gradcam_heatmap
from frequency_detector import get_frequency_detector
from gan_fingerprint import get_gan_detector
from diffusion_detector import get_diffusion_detector

load_dotenv()

app = FastAPI(
    title="AuthenticEye AI Detection Service",
    description="Research-grade deepfake detection: ensemble CNN + frequency + GAN fingerprint + diffusion analysis",
    version="5.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Globals ─────────────────────────────────────────────────────────────────
ensemble: EnsembleImageDetector = None
video_detector: TemporalVideoDetector = None
freq_detector = None
gan_detector = None
diff_detector = None


@app.on_event("startup")
async def startup():
    global ensemble, video_detector, freq_detector, gan_detector, diff_detector
    print("🚀 Loading AuthenticEye v5.0 AI models...")

    # Core ensemble
    ensemble = load_models()

    # Specialized detectors (run inference in separate threads to avoid GIL issues)
    loop = asyncio.get_event_loop()
    freq_detector = await loop.run_in_executor(None, get_frequency_detector)
    gan_detector = await loop.run_in_executor(None, get_gan_detector)
    diff_detector = await loop.run_in_executor(None, get_diffusion_detector)

    # Temporal video detector
    video_detector = TemporalVideoDetector(ensemble, num_frames=32)

    print(f"✅ All models loaded. Device: {'cuda' if torch.cuda.is_available() else 'cpu'}")


@app.get("/")
def home():
    return {
        "service": "AuthenticEye v5.0",
        "status": "online",
        "modules": ["ensemble", "frequency", "gan_fingerprint", "diffusion", "temporal_video"],
    }


@app.get("/health")
def health():
    return {"status": "healthy", "device": "cuda" if torch.cuda.is_available() else "cpu"}


# ─── Image Detection ─────────────────────────────────────────────────────────
@app.post("/detect/image")
async def detect_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    try:
        contents = await file.read()
        pil_image = Image.open(io.BytesIO(contents)).convert("RGB")

        # Run all detectors concurrently
        loop = asyncio.get_event_loop()

        # 1. Ensemble (EfficientNet + Xception + ViT)
        tensor, face_found = preprocess_image_for_ensemble(pil_image)

        # Run detectors in thread pool (CPU-bound)
        ensemble_result, freq_result, gan_result, diff_result = await asyncio.gather(
            loop.run_in_executor(None, ensemble.predict, tensor),
            loop.run_in_executor(None, freq_detector.predict, pil_image),
            loop.run_in_executor(None, gan_detector.predict, pil_image),
            loop.run_in_executor(None, diff_detector.predict, pil_image),
        )

        # 2. Weighted ensemble
        # NOTE: CNN models (eff/xcep/vit) use ImageNet pretrained weights only —
        # no deepfake fine-tuning. Their scores are unreliable.
        # Physics-based signals (freq/gan/diff) are grounded in forensic science
        # and work WITHOUT training data. Weight accordingly.
        eff_score  = ensemble_result["model_scores"]["efficientnet_b4"]
        xcep_score = ensemble_result["model_scores"]["xceptionnet"]
        vit_score  = ensemble_result["model_scores"]["vision_transformer"]
        freq_score = freq_result["frequency_score"]
        gan_score  = gan_result["gan_probability"]
        diff_score = diff_result["diffusion_probability"]

        # CNN models: 25% total weight (they are not fine-tuned)
        # Physics signals: 75% total weight (reliable without training)
        final_deepfake_prob = (
            0.08 * eff_score  +
            0.08 * xcep_score +
            0.09 * vit_score  +
            0.35 * freq_score +
            0.25 * gan_score  +
            0.15 * diff_score
        )
        final_deepfake_prob = round(min(0.99, max(0.01, final_deepfake_prob)), 4)

        # 3. Grad-CAM heatmap (async in thread)
        heatmap_b64 = await loop.run_in_executor(
            None, generate_gradcam_heatmap, ensemble, tensor, pil_image
        )

        return {
            "deepfake_probability": final_deepfake_prob,
            "authenticity_score": round(1.0 - final_deepfake_prob, 4),
            "face_detected": face_found,
            "heatmap_base64": heatmap_b64,
            "model_scores": {
                "efficientnet_b4": round(eff_score, 4),
                "xceptionnet": round(xcep_score, 4),
                "vision_transformer": round(vit_score, 4),
                "frequency_cnn": round(freq_score, 4),
                "gan_fingerprint": round(gan_score, 4),
                "diffusion_detector": round(diff_score, 4),
            },
            "gan_probability": round(gan_score, 4),
            "diffusion_probability": round(diff_score, 4),
            "spectral_features": freq_result.get("spectral_features", {}),
            "diffusion_analysis": diff_result.get("analysis", {}),
            "fingerprint_stats": gan_result.get("fingerprint_stats", {}),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")


# ─── Video Detection ──────────────────────────────────────────────────────────
@app.post("/detect/video")
async def detect_video(file: UploadFile = File(...)):
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="File must be a video.")

    try:
        contents = await file.read()
        result = await video_detector.analyze(contents, filename=file.filename)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video detection failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, workers=1)
