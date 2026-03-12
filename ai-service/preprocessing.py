"""
AuthenticEye — Step 6: Advanced Preprocessing with MediaPipe
Replaces OpenCV Haar cascades with MediaPipe Face Mesh for:
  - Accurate face detection
  - 468-point landmark detection  
  - Precise face alignment (roll correction)
  - Standardized face crop
"""
import cv2
import numpy as np
import torch
import torchvision.transforms as T
from PIL import Image
from typing import Tuple
import tempfile
import os

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

IMAGENET_TRANSFORM = T.Compose([
    T.Resize((224, 224)),
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# ─── MediaPipe Face Detection ──────────────────────────────────────────────────
try:
    import mediapipe as mp
    _mp_face_detection = mp.solutions.face_detection
    _mp_face_mesh = mp.solutions.face_mesh
    MEDIAPIPE_AVAILABLE = True
    print("✅ MediaPipe loaded for face alignment")
except (ImportError, AttributeError, Exception):
    MEDIAPIPE_AVAILABLE = False
    print("⚠️  MediaPipe not fully available — falling back to OpenCV Haar")

# OpenCV fallback
try:
    _face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    HAAR_AVAILABLE = True
except Exception:
    HAAR_AVAILABLE = False


def _align_face_mediapipe(pil_img: Image.Image) -> Tuple[Image.Image, bool]:
    """
    Uses MediaPipe Face Mesh for 468-point landmark detection.
    Performs geometric alignment based on eye positions (roll correction).
    """
    img_rgb = np.array(pil_img.convert("RGB"))
    h, w = img_rgb.shape[:2]

    with _mp_face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        min_detection_confidence=0.5,
        refine_landmarks=True,
    ) as face_mesh:
        results = face_mesh.process(img_rgb)

    if not results.multi_face_landmarks:
        return pil_img, False

    landmarks = results.multi_face_landmarks[0].landmark

    # Key landmarks (MediaPipe indices):
    # Left eye center: ~33, Right eye center: ~263
    # Nose tip: 1, Chin: 152
    left_eye = np.array([landmarks[33].x * w, landmarks[33].y * h])
    right_eye = np.array([landmarks[263].x * w, landmarks[263].y * h])

    # Compute roll angle
    dY = right_eye[1] - left_eye[1]
    dX = right_eye[0] - left_eye[0]
    angle = np.degrees(np.arctan2(dY, dX))

    # Face bounding box from all landmarks
    xs = [lm.x * w for lm in landmarks]
    ys = [lm.y * h for lm in landmarks]
    x1, y1 = int(max(0, min(xs))), int(max(0, min(ys)))
    x2, y2 = int(min(w, max(xs))), int(min(h, max(ys)))

    # Add margin
    margin_x = int((x2 - x1) * 0.25)
    margin_y = int((y2 - y1) * 0.25)
    x1 = max(0, x1 - margin_x)
    y1 = max(0, y1 - margin_y)
    x2 = min(w, x2 + margin_x)
    y2 = min(h, y2 + margin_y)

    # Rotate image to align eyes horizontally
    eye_center = tuple(((left_eye + right_eye) / 2).astype(int))
    M = cv2.getRotationMatrix2D(eye_center, angle, 1.0)
    aligned = cv2.warpAffine(img_rgb, M, (w, h), flags=cv2.INTER_CUBIC)

    # Crop face
    face_crop = aligned[y1:y2, x1:x2]
    if face_crop.size == 0:
        return pil_img, False

    return Image.fromarray(face_crop), True


def _detect_face_haar(pil_img: Image.Image) -> Tuple[Image.Image, bool]:
    """Fallback: OpenCV Haar Cascade face detection."""
    if not HAAR_AVAILABLE:
        return pil_img, False

    img_cv = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    faces = _face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))

    if len(faces) == 0:
        return pil_img, False

    areas = [(w * h, x, y, w, h) for (x, y, w, h) in faces]
    _, x, y, w, h = max(areas, key=lambda a: a[0])

    margin = int(0.25 * min(w, h))
    x1 = max(0, x - margin)
    y1 = max(0, y - margin)
    x2 = min(pil_img.width, x + w + margin)
    y2 = min(pil_img.height, y + h + margin)

    return pil_img.crop((x1, y1, x2, y2)), True


def preprocess_image_for_ensemble(pil_img: Image.Image) -> Tuple[torch.Tensor, bool]:
    """
    Full preprocessing pipeline with face alignment.
    Priority: MediaPipe (landmarks + alignment) > OpenCV Haar > Raw image
    Returns (tensor, face_found)
    """
    if MEDIAPIPE_AVAILABLE:
        face_img, found = _align_face_mediapipe(pil_img)
    else:
        face_img, found = _detect_face_haar(pil_img)

    tensor = IMAGENET_TRANSFORM(face_img).unsqueeze(0).to(DEVICE)
    return tensor, found


def extract_frames(video_bytes: bytes, num_frames: int = 32) -> list:
    """Extract evenly-spaced frames from video byte stream."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(video_bytes)
        tmp_path = f.name

    cap = cv2.VideoCapture(tmp_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if total == 0:
        cap.release()
        os.unlink(tmp_path)
        raise ValueError("Video has no frames.")

    step = max(1, total // num_frames)
    frames = []
    for i in range(num_frames):
        frame_id = min(i * step, total - 1)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
        ret, frame = cap.read()
        if ret:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(Image.fromarray(rgb))

    cap.release()
    os.unlink(tmp_path)
    return frames
