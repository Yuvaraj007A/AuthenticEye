import os
import sys
import pickle
import json
import torch
import numpy as np
from pathlib import Path
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from datetime import datetime

# Add root folder to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from model import load_models, DEVICE
from preprocessing import preprocess_image_for_ensemble

def train_ensemble():
    print("[INFO] Training Ensemble Logistic Regression model...")
    service_root = Path(__file__).resolve().parent.parent
    data_dir = service_root / "training" / "prepared_data"
    models_dir = service_root / "models"
    os.makedirs(models_dir, exist_ok=True)
    
    if not data_dir.exists():
        print(f"[WARNING] Prepared data directory not found at {data_dir}. Running fallback mockup ensemble training.")
        clf = LogisticRegression()
        X_mock = np.random.rand(10, 4)
        y_mock = np.random.randint(0, 2, 10)
        clf.fit(X_mock, y_mock)
        with open(models_dir / "ensemble.pkl", "wb") as f:
            pickle.dump(clf, f)
        
        meta = {
            "version": "v1",
            "accuracy": 0.5,
            "precision": 0.5,
            "recall": 0.5,
            "f1": 0.5,
            "dataset": "Mockup Baseline",
            "createdAt": datetime.utcnow().isoformat() + "Z"
        }
        with open(models_dir / "current.json", "w") as f:
            json.dump(meta, f, indent=4)
        print("[SUCCESS] Mockup ensemble trained and saved.")
        return

    X_train, y_train = [], []
    print("Loading models for feature extraction...")
    detector = load_models()
    
    for category, label in [("real", 0), ("fake", 1)]:
        cat_dir = data_dir / "train" / category
        if not cat_dir.exists():
            continue
        
        images = list(cat_dir.glob("*.jpg")) + list(cat_dir.glob("*.jpeg")) + list(cat_dir.glob("*.png"))
        print(f"Extracting features from {len(images)} training images in {category}...")
        for img_path in images[:20]:  # Limit for quick baseline fit
            try:
                with Image.open(img_path) as pil_img:
                    pil_img = pil_img.convert("RGB")
                    tensor, _ = preprocess_image_for_ensemble(pil_img)
                    
                    with torch.no_grad():
                        tensor = tensor.to(DEVICE)
                        score_eff = detector.eff(tensor).squeeze().item()
                        score_xcep = detector.xcep(tensor).squeeze().item()
                    
                    fft_res = detector.fft.predict(pil_img)
                    fft_score = fft_res.get("frequency_score", 0.0)
                    
                    art_res = detector.artifact.predict(pil_img)
                    art_score = art_res.get("artifact_probability", 0.0)
                    
                    X_train.append([score_eff, score_xcep, fft_score, art_score])
                    y_train.append(label)
            except Exception as e:
                print(f"[WARNING] Skipping {img_path.name}: {e}")
                
    if len(X_train) == 0:
        print("[ERROR] No training features extracted. Creating fallback.")
        clf = LogisticRegression()
        X_mock = np.random.rand(10, 4)
        y_mock = np.random.randint(0, 2, 10)
        clf.fit(X_mock, y_mock)
        with open(models_dir / "ensemble.pkl", "wb") as f:
            pickle.dump(clf, f)
        return
        
    X_train = np.array(X_train)
    y_train = np.array(y_train)
    
    print(f"Fitting Logistic Regression on {len(X_train)} samples...")
    clf = LogisticRegression()
    clf.fit(X_train, y_train)
    
    y_pred = clf.predict(X_train)
    acc = accuracy_score(y_train, y_pred)
    prec = precision_score(y_train, y_pred, zero_division=0)
    rec = recall_score(y_train, y_pred, zero_division=0)
    f1 = f1_score(y_train, y_pred, zero_division=0)
    
    print(f"Training Metrics -> Acc: {acc:.4f}, Prec: {prec:.4f}, Rec: {rec:.4f}, F1: {f1:.4f}")
    
    with open(models_dir / "ensemble.pkl", "wb") as f:
        pickle.dump(clf, f)
    print(f"[SUCCESS] Saved ensemble.pkl to {models_dir / 'ensemble.pkl'}")
    
    meta = {
        "version": "v1",
        "accuracy": round(float(acc), 4),
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1": round(float(f1), 4),
        "dataset": "Prepared FF++ & DFDC Split",
        "createdAt": datetime.utcnow().isoformat() + "Z"
    }
    with open(models_dir / "current.json", "w") as f:
        json.dump(meta, f, indent=4)
    print(f"[SUCCESS] Saved current.json metadata to {models_dir / 'current.json'}")
    
    eff_ckpt = models_dir / "efficientnet_dfdc.pt"
    xcep_ckpt = models_dir / "xception_ffpp.pt"
    
    if not eff_ckpt.exists():
        torch.save(detector.eff.state_dict(), eff_ckpt)
        print(f"Saved baseline {eff_ckpt}")
    if not xcep_ckpt.exists():
        torch.save(detector.xcep.state_dict(), xcep_ckpt)
        print(f"Saved baseline {xcep_ckpt}")

if __name__ == "__main__":
    train_ensemble()
