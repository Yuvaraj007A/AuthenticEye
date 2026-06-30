import os
import sys
import time
import datetime
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from pathlib import Path
import json
import pickle
import numpy as np
from PIL import Image

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from models.image_models import EfficientNetDetector
from training.dataset import DeepfakeDataset, train_transform, val_transform, get_balanced_sampler
from preprocessing import preprocess_image_for_ensemble
import version_manager

class MergedDeepfakeDataset(Dataset):
    """Dataset that merges baseline prepared training data with verified feedback samples."""
    def __init__(self, root_dirs, transform=None):
        self.samples = []
        self.transform = transform
        self.labels_list = []
        
        for root_dir in root_dirs:
            root_path = Path(root_dir)
            real_dir = root_path / "real"
            fake_dir = root_path / "fake"
            
            # Load real
            if real_dir.exists():
                for ext in ["**/*.jpg", "**/*.png", "**/*.jpeg", "**/*.JPG", "**/*.PNG", "**/*.JPEG"]:
                    for img_path in real_dir.glob(ext):
                        self.samples.append((str(img_path), 0.0))
                        self.labels_list.append(0)
                        
            # Load fake
            if fake_dir.exists():
                for ext in ["**/*.jpg", "**/*.png", "**/*.jpeg", "**/*.JPG", "**/*.PNG", "**/*.JPEG"]:
                    for img_path in fake_dir.glob(ext):
                        self.samples.append((str(img_path), 1.0))
                        self.labels_list.append(1)
                        
        print(f"Merged dataset loaded: {len(self.samples)} samples "
              f"({sum(1 for l in self.labels_list if l==0)} real, "
              f"{sum(1 for l in self.labels_list if l==1)} fake)")

    def __len__(self):
        return len(self.samples)

    from training.dataset import DeepfakeDataset
    # Reuse standard getitem logic
    __getitem__ = DeepfakeDataset.__getitem__


def run_retraining():
    """Runs retraining on CPU/GPU and outputs versioned weights and metrics."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Retraining starting on device: {device}")
    
    # Paths
    service_root = Path(__file__).resolve().parent.parent
    prepared_candidates = [
        service_root / "training" / "prepared_data",
        service_root / "prepared_data",
    ]
    prepared_root = next((p for p in prepared_candidates if (p / "train").exists()), prepared_candidates[0])
    base_train_dir = prepared_root / "train"
    base_val_dir = prepared_root / "val"
    verified_dir = service_root / "training" / "verified_data"
    root_verified_dir = service_root.parent / "feedback_dataset" / "verified_dataset"
    checkpoints_dir = service_root / "checkpoints"
    
    os.makedirs(checkpoints_dir, exist_ok=True)
    
    # 1. Load Data
    train_dirs = [base_train_dir]
    if os.path.exists(verified_dir):
        train_dirs.append(verified_dir)
    if os.path.exists(root_verified_dir):
        train_dirs.append(root_verified_dir)
        
    train_ds = MergedDeepfakeDataset(train_dirs, train_transform)
    val_ds = DeepfakeDataset(base_val_dir, val_transform)
    
    if len(train_ds) == 0:
        raise ValueError("No training samples found. Retraining aborted.")
    if len(val_ds) == 0:
        raise ValueError(f"No validation samples found at {base_val_dir}. Prepare a train/val dataset before retraining.")
        
    train_sampler = get_balanced_sampler(train_ds) if len(train_ds) > 0 else None
    
    train_loader = DataLoader(train_ds, batch_size=8, sampler=train_sampler, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=8, shuffle=False, num_workers=0)
    
    # Count verified samples used
    verified_real = 0
    verified_fake = 0
    for d in [verified_dir, root_verified_dir]:
        if os.path.exists(d):
            if os.path.exists(os.path.join(d, "real")):
                verified_real += len(list(Path(os.path.join(d, "real")).glob("*")))
            if os.path.exists(os.path.join(d, "fake")):
                verified_fake += len(list(Path(os.path.join(d, "fake")).glob("*")))
    total_verified = verified_real + verified_fake
    
    # 2. Instantiate Model and Load current best
    model = EfficientNetDetector(pretrained=True).to(device)
    models_dir = service_root / "models"
    os.makedirs(models_dir, exist_ok=True)
    current_best_path = os.path.join(models_dir, "efficientnet_dfdc.pt")
    if not os.path.exists(current_best_path):
        current_best_path = os.path.join(checkpoints_dir, "efficientnet_b4.pth")
        
    if os.path.exists(current_best_path):
        try:
            ckpt = torch.load(current_best_path, map_location=device)
            if isinstance(ckpt, dict) and "model_state" in ckpt:
                model.load_state_dict(ckpt["model_state"])
            else:
                model.load_state_dict(ckpt)
            print("[INFO] Fine-tuning on top of current active checkpoint")
        except Exception as e:
            print(f"[WARNING] Could not load current checkpoint, starting fresh: {e}")
            
    # 3. Training Loop (Streamlined 3 Epochs for CPU adaptive feedback learning)
    epochs = 3
    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.AdamW(model.parameters(), lr=5e-5, weight_decay=1e-4)
    
    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device).unsqueeze(1)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            
        print(f"Epoch {epoch+1}/{epochs} | Train Loss: {train_loss/len(train_loader):.4f}")
        
    # 4. Evaluation
    model.eval()
    val_correct = 0
    val_targets = []
    val_preds = []
    
    with torch.no_grad():
        for images, labels in val_loader:
            images, labels = images.to(device), labels.to(device).unsqueeze(1)
            outputs = model(images)
            probs = torch.sigmoid(outputs)
            preds = (probs > 0.5).float()
            val_correct += (preds == labels).sum().item()
            
            val_preds.extend(probs.cpu().numpy().flatten())
            val_targets.extend(labels.cpu().numpy().flatten())
            
    val_acc = val_correct / len(val_ds)
    
    from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score
    try:
        auc = roc_auc_score(val_targets, val_preds)
        binary_preds = [1 if p > 0.5 else 0 for p in val_preds]
        f1 = f1_score(val_targets, binary_preds)
        prec = precision_score(val_targets, binary_preds)
        rec = recall_score(val_targets, binary_preds)
    except Exception:
        auc, f1, prec, rec = 0.5, 0.0, 0.0, 0.0
        
    metrics = {
        "accuracy": round(float(val_acc), 4),
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1": round(float(f1), 4),
        "auc": round(float(auc), 4),
    }
    
    active_eff_path = os.path.join(models_dir, "efficientnet_dfdc.pt")
    torch.save(model.state_dict(), active_eff_path)
    print(f"[SUCCESS] Saved active serving EfficientNet to {active_eff_path}")
    
    # 5. Fit the Ensemble classifier using new EfficientNet
    from model import load_models
    detector = load_models()
    
    X_ens, y_ens = [], []
    print("[INFO] Re-training LogisticRegression ensemble on current models...")
    for category, label in [("real", 0), ("fake", 1)]:
        cat_dir = base_train_dir / category
        images = list(cat_dir.glob("*.jpg")) + list(cat_dir.glob("*.jpeg")) + list(cat_dir.glob("*.png"))
        for img_path in images[:150]:  # Limit for quick training
            try:
                with Image.open(img_path) as pil_img:
                    pil_img = pil_img.convert("RGB")
                    tensor, _ = preprocess_image_for_ensemble(pil_img)
                    with torch.no_grad():
                        tensor = tensor.to(device)
                        score_eff = torch.sigmoid(model(tensor)).squeeze().item()
                        score_xcep = detector.xcep(tensor).squeeze().item()
                    
                    fft_res = detector.fft.predict(pil_img)
                    fft_score = fft_res.get("frequency_score", 0.0)
                    
                    art_res = detector.artifact.predict(pil_img)
                    art_score = art_res.get("artifact_probability", 0.0)
                    
                    X_ens.append([score_eff, score_xcep, fft_score, art_score])
                    y_ens.append(label)
            except Exception as e:
                pass
                
    if len(X_ens) > 0:
        from sklearn.linear_model import LogisticRegression
        clf = LogisticRegression()
        clf.fit(np.array(X_ens), np.array(y_ens))
        with open(os.path.join(models_dir, "ensemble.pkl"), "wb") as f:
            pickle.dump(clf, f)
        print("[SUCCESS] Ensemble LogisticRegression retrained successfully.")
    
    # 6. Save Versioned Checkpoint (Phase 4 Versioning & Rotation)
    version_id = version_manager.get_next_version()
    v_dir = version_manager.create_version_checkpoint(version_id, metrics, "Merged Baseline & Verified Feedbacks")
    print(f"[SUCCESS] Versioned directory {version_id} created at {v_dir}")
    
    return {
        "version": version_id,
        "metrics": metrics,
        "efficientnetPath": os.path.join(v_dir, "efficientnet_dfdc.pt"),
        "xceptionnetPath": os.path.join(v_dir, "xception_ffpp.pt"),
        "vitPath": "",
        "trained_samples": total_verified
    }
