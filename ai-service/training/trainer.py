import os
import sys
import argparse
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
from pathlib import Path
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score, confusion_matrix
import numpy as np

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from models.image_models import EfficientNetDetector, XceptionDetector, ViTDetector
from training.dataset import DeepfakeDataset, train_transform, val_transform, get_balanced_sampler

class FocalLoss(nn.Module):
    """Focal Loss for hard-to-detect deepfakes."""
    def __init__(self, alpha=0.25, gamma=2.0, reduction='mean'):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction

    def forward(self, inputs, targets):
        BCE_loss = nn.functional.binary_cross_entropy_with_logits(inputs, targets, reduction='none')
        pt = torch.exp(-BCE_loss)
        F_loss = self.alpha * (1-pt)**self.gamma * BCE_loss
        
        if self.reduction == 'mean':
            return torch.mean(F_loss)
        elif self.reduction == 'sum':
            return torch.sum(F_loss)
        else:
            return F_loss

def train_model(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on: {device}")

    # Datasets
    train_dir = os.path.join(args.data_dir, "train")
    val_dir = os.path.join(args.data_dir, "val")
    
    train_ds = DeepfakeDataset(train_dir, train_transform)
    val_ds = DeepfakeDataset(val_dir, val_transform)
    
    # Sampler for class balancing
    train_sampler = get_balanced_sampler(train_ds) if len(train_ds) > 0 else None
    
    nw = 0 if sys.platform == "win32" else 4
    train_loader = DataLoader(
        train_ds, batch_size=args.batch_size, 
        sampler=train_sampler, 
        num_workers=nw, pin_memory=True
    )
    # Validation uses standard shuffle=False
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=nw, pin_memory=True)

    # Model selection
    model_map = {
        "efficientnet_b4": EfficientNetDetector,
        "xceptionnet": XceptionDetector,
        "vit": ViTDetector,
    }
    if args.model not in model_map:
        raise ValueError(f"Unknown model: {args.model}")

    model = model_map[args.model](pretrained=True).to(device)

    if torch.cuda.device_count() > 1:
        print(f"Using {torch.cuda.device_count()} GPUs")
        model = nn.DataParallel(model)

    # Optimizer + Scheduler
    if args.loss == 'focal':
        criterion = FocalLoss()
    else:
        criterion = nn.BCEWithLogitsLoss()
        
    optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    # Cosine annealing with linear warmup could be added via sequential scheduler, 
    # but for simplicity we rely on CosineAnnealingLR directly
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    
    # AMP Scaler
    scaler = torch.cuda.amp.GradScaler(enabled=args.use_amp)

    writer = SummaryWriter(log_dir=args.log_dir)
    os.makedirs(args.checkpoint_dir, exist_ok=True)

    best_val_auc = 0.0
    start_epoch = 0
    patience_counter = 0

    if args.resume and os.path.exists(args.resume):
        ckpt = torch.load(args.resume, map_location=device)
        model.load_state_dict(ckpt["model_state"])
        optimizer.load_state_dict(ckpt["optimizer_state"])
        if "scaler_state" in ckpt and args.use_amp:
            scaler.load_state_dict(ckpt["scaler_state"])
        start_epoch = ckpt["epoch"] + 1
        best_val_auc = ckpt.get("best_val_auc", 0.0)
        print(f"Resumed from epoch {start_epoch}")

    for epoch in range(start_epoch, args.epochs):
        # ─── Training Phase
        model.train()
        train_loss, train_correct = 0.0, 0
        train_preds, train_targets = [], []
        
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device).unsqueeze(1)
            optimizer.zero_grad()
            
            with torch.cuda.amp.autocast(enabled=args.use_amp):
                outputs = model(images)
                loss = criterion(outputs, labels)
                
            scaler.scale(loss).backward()
            
            # Gradient Clipping
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            
            scaler.step(optimizer)
            scaler.update()
            
            train_loss += loss.item()
            
            # Compute accuracy from logits
            probs = torch.sigmoid(outputs)
            preds = (probs > 0.5).float()
            train_correct += (preds == labels).sum().item()
            
            train_preds.extend(probs.detach().cpu().numpy())
            train_targets.extend(labels.detach().cpu().numpy())

        scheduler.step()
        train_acc = train_correct / max(1, len(train_ds)) * 100

        # ─── Validation Phase
        model.eval()
        val_loss, val_correct = 0.0, 0
        val_preds, val_targets = [], []
        
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device).unsqueeze(1)
                
                with torch.cuda.amp.autocast(enabled=args.use_amp):
                    outputs = model(images)
                    loss = criterion(outputs, labels)
                    
                val_loss += loss.item()
                
                probs = torch.sigmoid(outputs)
                preds = (probs > 0.5).float()
                val_correct += (preds == labels).sum().item()
                
                val_preds.extend(probs.detach().cpu().numpy())
                val_targets.extend(labels.detach().cpu().numpy())

        val_acc = val_correct / max(1, len(val_ds)) * 100
        
        # Scikit-learn metrics
        val_targets_flat = np.array(val_targets).flatten()
        val_preds_flat = np.array(val_preds).flatten()
        val_preds_binary = (val_preds_flat > 0.5).astype(int)
        
        try:
            val_auc = roc_auc_score(val_targets_flat, val_preds_flat)
            val_f1 = f1_score(val_targets_flat, val_preds_binary)
            val_precision = precision_score(val_targets_flat, val_preds_binary)
            val_recall = recall_score(val_targets_flat, val_preds_binary)
            # cm = confusion_matrix(val_targets_flat, val_preds_binary)
        except ValueError:
            # Fallback if only one class is present in validation batch
            val_auc, val_f1, val_precision, val_recall = 0,0,0,0

        print(f"Epoch [{epoch+1}/{args.epochs}] "
              f"Train Loss: {train_loss/max(1, len(train_loader)):.4f} Acc: {train_acc:.2f}% | "
              f"Val Loss: {val_loss/max(1, len(val_loader)):.4f} Acc: {val_acc:.2f}% "
              f"AUC: {val_auc:.4f} F1: {val_f1:.4f}")

        writer.add_scalar("Loss/train", train_loss/max(1, len(train_loader)), epoch)
        writer.add_scalar("Loss/val", val_loss/max(1, len(val_loader)), epoch)
        writer.add_scalar("Metrics/AUC", val_auc, epoch)
        writer.add_scalar("Metrics/F1", val_f1, epoch)

        # Save best checkpoint & Early Stopping
        if val_auc > best_val_auc:
            best_val_auc = val_auc
            patience_counter = 0
            ckpt_path = os.path.join(args.checkpoint_dir, f"{args.model}_best.pth")
            state = model.module.state_dict() if hasattr(model, "module") else model.state_dict()
            torch.save({
                "epoch": epoch,
                "model_state": state,
                "optimizer_state": optimizer.state_dict(),
                "scaler_state": scaler.state_dict() if args.use_amp else None,
                "best_val_auc": best_val_auc,
            }, ckpt_path)
            print(f"  ✅ New best checkpoint saved: {ckpt_path} (AUC={val_auc:.4f})")
        else:
            patience_counter += 1
            if patience_counter >= args.patience:
                print(f"Early stopping triggered after {patience_counter} epochs.")
                break

    writer.close()
    print(f"\nTraining complete. Best Val AUC: {best_val_auc:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AuthenticEye Research Training Pipeline")
    parser.add_argument("--model", type=str, default="efficientnet_b4", choices=["efficientnet_b4", "xceptionnet", "vit"])
    parser.add_argument("--data_dir", type=str, required=True, help="Path to dataset")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--use_amp", action="store_true", help="Use Automatic Mixed Precision")
    parser.add_argument("--loss", type=str, default="bce", choices=["bce", "focal"])
    parser.add_argument("--patience", type=int, default=10, help="Early stopping patience")
    parser.add_argument("--checkpoint_dir", type=str, default="../checkpoints")
    parser.add_argument("--log_dir", type=str, default="../tensorboard_logs")
    parser.add_argument("--resume", type=str, default=None)
    args = parser.parse_args()
    train_model(args)
