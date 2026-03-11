# AuthenticEye — Forensic-Grade Deepfake Detection Platform

A production-ready, SaaS-architecture deepfake detection platform capable of detecting manipulated images, videos, and audio using a state-of-the-art ensemble of deep learning models.

---

## System Architecture

```
Client Browser
    ↓
React Frontend (Vite + TailwindCSS + Framer Motion)
    ↓
Express.js Backend API (Node.js + JWT + Multer)
    ↓
FastAPI AI Microservice (Python + PyTorch)
    ↓
Ensemble Detection Models
  ├─ EfficientNet-B4
  ├─ XceptionNet
  └─ Vision Transformer (ViT-B/16)
    ↓
MongoDB Atlas (Analysis Storage)
Redis (Queue — future job processing)
```

---

## AI Detection Capabilities

| Media Type | Method | Models |
|---|---|---|
| Image | Face crop → ELA → Ensemble | EfficientNet-B4, XceptionNet, ViT |
| Video | Frame extraction → Per-frame ensemble | Same as image |
| Audio | Mel Spectrogram → CNN | MobileNetV3-Small |
| Explainability | Grad-CAM heatmaps | EfficientNet primary model |

---

## Quick Start (Local Development)

### Prerequisites
- Node.js ≥ 18
- Python ≥ 3.10
- MongoDB running locally (or Atlas URI)

### 1. Backend Setup
```bash
cd backend
cp ../.env.example .env   # Edit values
npm install
npm run dev
```

### 2. AI Service Setup
```bash
cd ai-service
python -m venv venv
venv\Scripts\activate     # Windows
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend Setup
```bash
cd frontend
echo "VITE_API_URL=http://localhost:5000/api" > .env
npm install
npm run dev
```

---

## Docker Deployment

```bash
# Copy and configure env
cp .env.example .env

# Build and start all services
docker compose up --build -d

# Enable GPU (requires nvidia-container-toolkit)
# Uncomment the `deploy.resources` section in docker-compose.yml
```

Services will be available at:
- Frontend: http://localhost:80
- Backend API: http://localhost:5000
- AI Service: http://localhost:8000

---

## Training Your Own Model

Fine-tune on FaceForensics++, DFDC, Celeb-DF, or DeeperForensics:

```bash
# Prepare dataset in:
# data/train/real/  ← real images
# data/train/fake/  ← fake images
# data/val/real/
# data/val/fake/

cd training

# Train EfficientNet-B4
python train.py --model efficientnet_b4 --data_dir ../data --epochs 30 --batch_size 32

# Train XceptionNet
python train.py --model xceptionnet --data_dir ../data --epochs 30

# Train ViT
python train.py --model vit --data_dir ../data --epochs 30

# Monitor with Tensorboard
tensorboard --logdir ./tensorboard_logs
```

Checkpoints are automatically saved to `ai-service/checkpoints/` and loaded on next service start.

---

## API Reference

### Image Detection
```
POST /api/detect/image
Content-Type: multipart/form-data
Body: image (file)
```

### Video Detection
```
POST /api/detect/video
Content-Type: multipart/form-data
Body: video (file)  [max 500MB]
```

### Audio Detection
```
POST /api/detect/audio
Content-Type: multipart/form-data
Body: audio (file)  [max 50MB]
```

### Analysis History (Authenticated)
```
GET    /api/history
GET    /api/history/:id
DELETE /api/history/:id
```

---

## Result Schema
```json
{
  "deepfakeProbability": 0.9312,
  "authenticityScore": 0.0688,
  "mediaType": "image",
  "faceDetected": true,
  "modelScores": {
    "efficientnet_b4": 0.94,
    "xceptionnet": 0.91,
    "vision_transformer": 0.88
  },
  "heatmapBase64": "<base64 JPEG for Grad-CAM overlay>",
  "aiDetail": { ... }
}
```

---

## GPU Inference

The AI service automatically uses CUDA if available:

```python
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(DEVICE)
```

For Docker GPU, uncomment the `deploy.resources` section in `docker-compose.yml` and ensure `nvidia-container-toolkit` is installed.

---

## Security Features

- JWT authentication with expiry
- Helmet.js HTTP security headers
- Rate limiting (100 req / 15 min per IP)
- File type validation (MIME + extension)
- Upload size limits per media type
- CORS protection
- Files deleted immediately after processing

---

## Project Structure

```
AuthenticEye/
├── frontend/          # React + Vite + TailwindCSS
│   └── src/
│       ├── components/
│       │   ├── DeepfakeAnalyzer.jsx
│       │   ├── HeatmapViewer.jsx
│       │   ├── ResultCard.jsx
│       │   └── ...
│       └── pages/
├── backend/           # Node.js + Express + MongoDB
│   ├── routes/        # auth.js, detect.js, history.js
│   └── models/        # User.js, Analysis.js
├── ai-service/        # Python FastAPI + PyTorch
│   ├── main.py        # API entrypoint
│   ├── model.py       # Ensemble (EfficientNet + Xception + ViT)
│   ├── preprocessing.py # Face detection + ELA
│   ├── gradcam.py     # Explainability heatmaps
│   ├── video_detector.py
│   └── audio_detector.py
├── training/          # Training pipeline
│   └── train.py       # Multi-GPU, TensorBoard, checkpoints
└── docker-compose.yml
```
