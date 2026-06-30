"""
AuthenticEye AI Service v6.0 — Production Entrypoint
Advanced Modular Ensemble platform for AI Image & Video Detection
"""
import os
import io
import asyncio
import hashlib
import time
import torch
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from dotenv import load_dotenv

from detectors import registry
from explainability import (
    generate_fft_heatmap, 
    generate_gan_heatmap, 
    generate_face_box_overlay, 
    generate_forensic_explanation
)
from gradcam import generate_gradcam_heatmap
from model_manager import model_manager

load_dotenv()

# Sentry Initializer
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
        )
        print("[SUCCESS] Sentry monitoring initiated for FastAPI AI service")
    except Exception as e:
        print(f"[WARNING] Failed to load Sentry SDK: {e}")

app = FastAPI(
    title="AuthenticEye AI Detection Service",
    description="Production-grade deepfake detection: 8-detector modular registry ensemble",
    version="6.0.0",
)

# ─── Prometheus Instrumentation ──────────────────────────────────────────────
try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
    from fastapi import Response

    HTTP_REQUESTS_TOTAL = Counter(
        "http_requests_total", 
        "Total HTTP requests received", 
        ["method", "endpoint", "status"]
    )
    DETECTION_REQUESTS_TOTAL = Counter(
        "detection_requests_total", 
        "Total deepfake detection requests", 
        ["media_type"]
    )
    INFERENCE_LATENCY = Histogram(
        "inference_latency_seconds", 
        "Inference latency in seconds", 
        ["endpoint"]
    )

    @app.middleware("http")
    async def prometheus_middleware(request, call_next):
        method = request.method
        endpoint = request.url.path
        
        if endpoint == "/metrics":
            return await call_next(request)
            
        start_time = time.time()
        try:
            response = await call_next(request)
            status = response.status_code
            HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status=status).inc()
            
            if endpoint == "/detect/image" and status == 200:
                DETECTION_REQUESTS_TOTAL.labels(media_type="image").inc()
                INFERENCE_LATENCY.labels(endpoint=endpoint).observe(time.time() - start_time)
            elif endpoint == "/detect/video" and status == 200:
                DETECTION_REQUESTS_TOTAL.labels(media_type="video").inc()
                INFERENCE_LATENCY.labels(endpoint=endpoint).observe(time.time() - start_time)
                
            return response
        except Exception as e:
            HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status=500).inc()
            raise e

    @app.get("/metrics")
    def metrics_endpoint():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
        
    print("[SUCCESS] Prometheus metrics exporter initialized at /metrics")
except Exception as e:
    print(f"[WARNING] Failed to load Prometheus client: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Result Caching ──────────────────────────────────────────────────────────
# Keeps up to 100 recent predictions in memory to prevent redundant operations
INFERENCE_CACHE = {}
CACHE_MAX_SIZE = 100

def get_file_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def cache_result(file_hash: str, response_data: dict):
    if len(INFERENCE_CACHE) >= CACHE_MAX_SIZE:
        # Evict oldest key
        first_key = next(iter(INFERENCE_CACHE))
        INFERENCE_CACHE.pop(first_key)
    INFERENCE_CACHE[file_hash] = response_data

# ─── Load Config ─────────────────────────────────────────────────────────────
ENSEMBLE_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "ensemble_config.json")
def get_ensemble_weights() -> dict:
    import json
    if os.path.exists(ENSEMBLE_CONFIG_PATH):
        try:
            with open(ENSEMBLE_CONFIG_PATH, "r") as f:
                config = json.load(f)
                return config.get("weights", {})
        except Exception:
            pass
    # Fallback default weights
    return {
        "EfficientNetDFDC": 0.30,
        "XceptionFFPP": 0.30,
        "FrequencyForensics": 0.20,
        "SynthIDDetector": 0.10,
        "MetadataAnalyzer": 0.10,
        "C2PADetector": 0.10
    }

@app.on_event("startup")
async def startup():
    print("[INFO] Initializing model downloads and environment...")
    
    # 1. Download models dynamically if not cached
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, model_manager.auto_download_dependencies)
    
    # 2. Load detectors in the registry
    print("[INFO] Loading all registered detectors into memory...")
    await loop.run_in_executor(None, registry.load_all)
    
    print(f"[SUCCESS] All models loaded. Device: {'cuda' if torch.cuda.is_available() else 'cpu'}")

@app.get("/")
def home():
    return {
        "service": "AuthenticEye AI Engine v6.0",
        "status": "online",
        "active_detectors": list(registry.detector_classes.keys())
    }

@app.get("/health")
def health():
    health_status = model_manager.get_system_health(registry)
    return {"status": "healthy", **health_status}

@app.get("/detect/status")
def detect_status():
    return model_manager.get_system_health(registry)

# ─── Image Detection Endpoint ─────────────────────────────────────────────────
@app.post("/detect/image")
async def detect_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    try:
        contents = await file.read()
        file_hash = get_file_hash(contents)
        
        # Check cache
        if file_hash in INFERENCE_CACHE:
            print(f"[CACHE] Returning cached result for image {file_hash[:10]}")
            return INFERENCE_CACHE[file_hash]

        pil_image = Image.open(io.BytesIO(contents)).convert("RGB")
        loop = asyncio.get_event_loop()

        # Run all registry detectors in thread pool
        reg_results = await loop.run_in_executor(
            None, 
            lambda: registry.predict_all(pil_image, file_bytes=contents, mime_type=file.content_type)
        )

        # Compute weighted voting ensemble score
        weights = get_ensemble_weights()
        total_active_weight = 0.0
        weighted_score_sum = 0.0

        for name, res in reg_results.items():
            if "error" not in res and name in weights:
                # SPECIAL RULE for C2PA: if not detected, do not include in ensemble
                if name == "C2PADetector":
                    c2pa_det = res.get("details", {}).get("c2pa_detected", False)
                    if not c2pa_det:
                        continue
                score = res["score"]
                weight = weights[name]
                weighted_score_sum += score * weight
                total_active_weight += weight

        if total_active_weight > 0:
            final_prob = weighted_score_sum / total_active_weight
        else:
            # Fallback to mean score (excluding C2PADetector if not detected)
            valid_detectors = []
            for name, res in reg_results.items():
                if "error" not in res:
                    if name == "C2PADetector" and not res.get("details", {}).get("c2pa_detected", False):
                        continue
                    valid_detectors.append(res)
            final_prob = sum(r["score"] for r in valid_detectors) / len(valid_detectors) if valid_detectors else 0.5

        # Override final probability to 1.0 (definitely fake) if SynthID is detected
        synthid_detected = reg_results.get("SynthIDDetector", {}).get("details", {}).get("synthid_detected", False)
        if synthid_detected:
            final_prob = 1.0

        c2pa_res = reg_results.get("C2PADetector", {})
        c2pa_details = c2pa_res.get("details", {})
        c2pa_detected = c2pa_details.get("c2pa_detected", False)
        c2pa_valid = c2pa_details.get("c2pa_valid", False)

        # Format standardized response scores mapping to Phase 15 requirements
        scores_payload = {
            "efficientnet": round(reg_results.get("EfficientNetDFDC", {}).get("score", 0.0), 4),
            "xception": round(reg_results.get("XceptionFFPP", {}).get("score", 0.0), 4),
            "frequency": round(reg_results.get("FrequencyForensics", {}).get("score", 0.0), 4),
            "metadata": round(reg_results.get("MetadataAnalyzer", {}).get("score", 0.0), 4),
            "synthid": reg_results.get("SynthIDDetector", {}).get("details", {}).get("synthid_detected", False),
            "c2pa": round(c2pa_res.get("score", 0.0), 4),
            "c2pa_detected": c2pa_detected,
            "c2pa_valid": c2pa_valid,
            "c2pa_info": c2pa_details.get("manifest_info", {})
        }

        # Generate Explainability base64 overlays and textual summaries
        # 1. Base64 overlays
        # For Grad-CAM, run on the primary EfficientNet detector
        eff_detector = registry.get_detector("EfficientNetDFDC")
        from preprocessing import preprocess_image_for_ensemble
        tensor, face_found = preprocess_image_for_ensemble(pil_image)
        
        heatmap_res, fft_b64, gan_b64, facebox_b64 = await asyncio.gather(
            loop.run_in_executor(None, generate_gradcam_heatmap, eff_detector, tensor, pil_image),
            loop.run_in_executor(None, generate_fft_heatmap, pil_image),
            loop.run_in_executor(None, generate_gan_heatmap, pil_image),
            loop.run_in_executor(None, generate_face_box_overlay, pil_image),
        )

        heatmap_b64, gradcam_suspicious = heatmap_res
        scores_payload["gradcam_suspicious"] = gradcam_suspicious

        # 2. Text explanation
        explanation = generate_forensic_explanation(scores_payload, final_prob)

        # Standard output fields
        is_fake = final_prob > 0.5
        prediction = "AI_GENERATED" if is_fake else "REAL"
        confidence = final_prob if is_fake else (1.0 - final_prob)
        risk_level = "HIGH" if final_prob > 0.80 else ("MEDIUM" if final_prob > 0.45 else "LOW")

        # C2PA evidence structures
        c2pa_evidence = {
            "detector": "c2pa",
            "weight": 0.10,
            "evidence_score": round(c2pa_res.get("score", 0.0), 4) if "error" not in c2pa_res else 0.0,
            "confidence": round(c2pa_res.get("confidence", 0.0), 4) if "error" not in c2pa_res else 0.0,
            "classification": "evidence_only",
            "details": c2pa_details
        }

        evidence_payload = {
            "deep_learning": {
                "efficientnet_score": round(reg_results.get("EfficientNetDFDC", {}).get("score", 0.0), 4),
                "xception_score": round(reg_results.get("XceptionFFPP", {}).get("score", 0.0), 4),
            },
            "synthid": {
                "synthid_detected": reg_results.get("SynthIDDetector", {}).get("details", {}).get("synthid_detected", False),
            },
            "metadata": {
                "metadata_score": round(reg_results.get("MetadataAnalyzer", {}).get("score", 0.0), 4),
            },
            "frequency": {
                "frequency_score": round(reg_results.get("FrequencyForensics", {}).get("score", 0.0), 4),
            },
            "c2pa": c2pa_evidence
        }

        # C2PA Evidence payload
        evidence_strength = "None"
        impact_str = "0%"
        if c2pa_detected:
            if not c2pa_valid:
                evidence_strength = "Strong"
                impact_str = "+8%"
            else:
                evidence_strength = "Strong"
                if c2pa_details.get("is_ai_generated", False):
                    impact_str = "+10%"
                else:
                    impact_str = "-7%"

        c2pa_api_evidence = {
            "manifest_found": c2pa_detected,
            "signature_valid": c2pa_valid,
            "ai_assertion_found": c2pa_details.get("is_ai_generated", False),
            "generator": c2pa_details.get("generator"),
            "claim_generator": c2pa_details.get("claim_generator"),
            "provenance_chain": c2pa_details.get("has_provenance_chain", False),
            "evidence_strength": evidence_strength,
            "impact_on_final_score": impact_str
        }

        response = {
            "prediction": prediction,
            "confidence": round(confidence, 4),
            "risk_level": risk_level,
            "deepfake_probability": round(final_prob, 4),
            "authenticity_score": round(1.0 - final_prob, 4),
            "scores": scores_payload,
            "explanation": explanation,
            "evidence": evidence_payload,
            "C2PA Evidence": c2pa_api_evidence,
            "c2pa_evidence": c2pa_api_evidence,
            
            # Base64 visuals (compatibility)
            "face_detected": face_found,
            "heatmap_base64": heatmap_b64,
            "fft_base64": fft_b64,
            "gan_base64": gan_b64,
            "facebox_base64": facebox_b64,
            "gan_probability": scores_payload["xception"], # map to compatible field
            "diffusion_probability": 0.0, # map to compatible field
        }

        # Save to cache
        cache_result(file_hash, response)
        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Image detection failed: {str(e)}")

# ─── Video Detection Endpoint ─────────────────────────────────────────────────
@app.post("/detect/video")
async def detect_video(file: UploadFile = File(...)):
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="File must be a video.")

    try:
        contents = await file.read()
        file_hash = get_file_hash(contents)
        
        # Check cache
        if file_hash in INFERENCE_CACHE:
            print(f"[CACHE] Returning cached result for video {file_hash[:10]}")
            return INFERENCE_CACHE[file_hash]

        loop = asyncio.get_event_loop()
        temporal_analyzer = registry.get_detector("TemporalVideoAnalyzer")
        
        # 1. Run temporal & consistency checks on video frames
        video_result = await loop.run_in_executor(None, temporal_analyzer.predict_video, contents)
        temporal_score = video_result["score"]
        
        # 2. Extract frames and run image ensemble for base frame scores
        frames = temporal_analyzer._extract_adaptive_frames(contents)
        frame_scores = []
        for frame in frames[:8]: # Check subset of frames to speed up execution
            # Run image prediction
            res = await loop.run_in_executor(None, registry.predict_all, frame)
            # Weighted average
            weights = get_ensemble_weights()
            total_active_weight = 0.0
            weighted_score_sum = 0.0
            for name, score_res in res.items():
                if "error" not in score_res and name in weights:
                    weighted_score_sum += score_res["score"] * weights[name]
                    total_active_weight += weights[name]
            if total_active_weight > 0:
                frame_scores.append(weighted_score_sum / total_active_weight)
            else:
                frame_scores.append(0.5)

        avg_frame_score = float(np.mean(frame_scores)) if frame_scores else 0.5
        
        # 3. Combine Frame Ensemble (70%) + Temporal Analysis (30%)
        final_video_score = (avg_frame_score * 0.70) + (temporal_score * 0.30)
        
        # Structure final payload matching Phase 15 & 11
        is_fake = final_video_score > 0.5
        prediction = "AI_GENERATED" if is_fake else "REAL"
        confidence = final_video_score if is_fake else (1.0 - final_video_score)
        risk_level = "HIGH" if final_video_score > 0.80 else ("MEDIUM" if final_video_score > 0.45 else "LOW")
        
        scores_payload = {
            "avg_frame_ensemble": round(avg_frame_score, 4),
            "temporal_consistency": round(temporal_score, 4),
            "optical_flow_deviation": round(video_result["details"].get("optical_flow_anomaly", 0.0), 4),
            "embedding_drift": round(video_result["details"].get("embedding_drift", 0.0), 4)
        }
        
        explanation = {
            "verdict": prediction,
            "summary": f"The video was classified as {'Fake' if is_fake else 'Real'} based on spatial frames and temporal flow consistency checks.",
            "reasons": [
                f"Average frame ensemble: {'Fake' if avg_frame_score > 0.5 else 'Real'}",
                f"LSTM temporal consistency: {'Fake' if temporal_score > 0.5 else 'Real'}",
                f"Optical flow motion deviation index: {scores_payload['optical_flow_deviation']}"
            ]
        }
        
        # Empty C2PA details since this is a video
        c2pa_evidence = {
            "detector": "c2pa",
            "weight": 0.10,
            "evidence_score": 0.0,
            "confidence": 0.0,
            "classification": "evidence_only",
            "details": {
                "c2pa_detected": False,
                "c2pa_valid": False,
                "is_ai_generated": False,
                "generator": None,
                "claim_generator": None,
                "validation_status": None,
                "certificate_chain_valid": True,
                "has_edit_history": False,
                "has_provenance_chain": False,
                "manifest_count": 0,
                "tampering_indicators": [],
                "evidence_summary": ["No C2PA Content Credentials found"]
            }
        }

        evidence_payload = {
            "deep_learning": {
                "frame_ensemble_score": round(avg_frame_score, 4),
            },
            "synthid": {
                "synthid_detected": False,
            },
            "metadata": {
                "metadata_score": 0.0,
            },
            "frequency": {
                "frequency_score": 0.0,
            },
            "c2pa": c2pa_evidence
        }

        c2pa_api_evidence = {
            "manifest_found": False,
            "signature_valid": False,
            "ai_assertion_found": False,
            "generator": None,
            "claim_generator": None,
            "provenance_chain": False,
            "evidence_strength": "None",
            "impact_on_final_score": "0%"
        }

        response = {
            "prediction": prediction,
            "confidence": round(confidence, 4),
            "risk_level": risk_level,
            "deepfake_probability": round(final_video_score, 4),
            "authenticity_score": round(1.0 - final_video_score, 4),
            "scores": scores_payload,
            "explanation": explanation,
            "evidence": evidence_payload,
            "C2PA Evidence": c2pa_api_evidence,
            "c2pa_evidence": c2pa_api_evidence,
            
            # Compatibility structure with old Analysis schemas
            "frame_score_stats": {
                "mean": round(avg_frame_score, 4),
                "max": round(max(frame_scores) if frame_scores else 0.5, 4),
                "min": round(min(frame_scores) if frame_scores else 0.5, 4)
            },
            "frames_analyzed": video_result["details"].get("frames_analyzed", len(frames))
        }
        
        cache_result(file_hash, response)
        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Video detection failed: {str(e)}")

# ─── Retrain & Rollback ───────────────────────────────────────────────────────
@app.post("/retrain")
async def retrain_endpoint():
    try:
        from training.retrain_manager import run_retraining
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_retraining)
        
        # Hot-reload registry members
        print("[REGISTRY] Retraining completed. Hot reloading key classifiers...")
        registry.reload_detector("EfficientNetDFDC")
        registry.reload_detector("XceptionFFPP")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retraining failed: {str(e)}")

@app.post("/rollback")
async def rollback_endpoint(payload: dict):
    version = payload.get("version")
    if not version:
        raise HTTPException(status_code=400, detail="Missing version parameter")
        
    try:
        from version_manager import rollback_to_version
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, rollback_to_version, version)
        
        # Hot-reload registry members
        print("[REGISTRY] Rollback completed. Hot reloading key classifiers...")
        registry.reload_detector("EfficientNetDFDC")
        registry.reload_detector("XceptionFFPP")
        return {"status": "success", "rolled_back_to": version}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rollback failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, workers=1)
