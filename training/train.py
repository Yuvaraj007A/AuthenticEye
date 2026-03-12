"""
AuthenticEye — Training Pipeline
Supports: FaceForensics++, DFDC, Celeb-DF, DeeperForensics
Multi-GPU | Tensorboard | Checkpoint Saving | Resume Training
"""
import os
import sys
import argparse
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torch.utils.tensorboard import SummaryWriter
from torchvision import transforms
from PIL import Image
import numpy as np
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent / "ai-service"))
from model import EfficientNetDetector, XceptionDetector, ViTDetector

# ─── Dataset ─────────────────────────────────────────────────────────────────

class DeepfakeDataset(Dataset):
    """
    Universal deepfake dataset loader.
    Expects folder structure:
      data/
        real/  ← authentic images
        fake/  ← deepfake images
    Compatible with: FaceForensics++, DFDC, Celeb-DF, DeeperForensics
    """
    def __init__(self, root_dir: str, transform=None):
        self.samples = []
        self.transform = transform

        real_dir = Path(root_dir) / "real"
        fake_dir = Path(root_dir) / "fake"

        for img_path in real_dir.glob("**/*.jpg"):
            self.samples.append((str(img_path), 0.0))
        for img_path in real_dir.glob("**/*.png"):
            self.samples.append((str(img_path), 0.0))
        for img_path in fake_dir.glob("**/*.jpg"):
            self.samples.append((str(img_path), 1.0))
        for img_path in fake_dir.glob("**/*.png"):
            self.samples.append((str(img_path), 1.0))

        print(f"Dataset loaded: {len(self.samples)} samples "
              f"({sum(1 for _,l in self.samples if l==0)} real, "
              f"{sum(1 for _,l in self.samples if l==1)} fake)")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        image = Image.open(img_path).convert("RGB")
        if self.transform:
            image = self.transform(image)
        return image, torch.tensor(label, dtype=torch.float32)


# ─── Augmentation ─────────────────────────────────────────────────────────────

TRAIN_TRANSFORM = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.RandomCrop(224),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1),
    transforms.RandomRotation(10),
    transforms.RandomGrayscale(p=0.05),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

VAL_TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


# ─── Training Loop ─────────────────────────────────────────────────────────────

def train_model(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on: {device}")

    # Datasets
    train_ds = DeepfakeDataset(os.path.join(args.data_dir, "train"), TRAIN_TRANSFORM)
    val_ds = DeepfakeDataset(os.path.join(args.data_dir, "val"), VAL_TRANSFORM)
    # num_workers=0 required on Windows (multiprocessing fork issues)
    nw = 0 if sys.platform == "win32" else 4
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=nw)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=nw)

    # Model selection
    model_map = {
        "efficientnet_b4": EfficientNetDetector,
        "xceptionnet": XceptionDetector,
        "vit": ViTDetector,
    }
    if args.model not in model_map:
        raise ValueError(f"Unknown model: {args.model}. Choose from {list(model_map.keys())}")

    model = model_map[args.model]().to(device)

    # Multi-GPU support
    if torch.cuda.device_count() > 1:
        print(f"Using {torch.cuda.device_count()} GPUs")
        model = nn.DataParallel(model)

    # Optimizer + Scheduler
    criterion = nn.BCELoss()
    optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    # Tensorboard
    writer = SummaryWriter(log_dir=args.log_dir)
    os.makedirs(args.checkpoint_dir, exist_ok=True)

    best_val_acc = 0.0
    start_epoch = 0

    # Resume from checkpoint
    if args.resume and os.path.exists(args.resume):
        ckpt = torch.load(args.resume, map_location=device)
        model.load_state_dict(ckpt["model_state"])
        optimizer.load_state_dict(ckpt["optimizer_state"])
        start_epoch = ckpt["epoch"] + 1
        best_val_acc = ckpt.get("best_val_acc", 0.0)
        print(f"Resumed from epoch {start_epoch}")

    for epoch in range(start_epoch, args.epochs):
        # ─── Training Phase
        model.train()
        train_loss, train_correct = 0.0, 0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device).unsqueeze(1)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            preds = (outputs > 0.5).float()
            train_correct += (preds == labels).sum().item()

        scheduler.step()
        train_acc = train_correct / len(train_ds) * 100

        # ─── Validation Phase
        model.eval()
        val_loss, val_correct = 0.0, 0
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device).unsqueeze(1)
                outputs = model(images)
                val_loss += criterion(outputs, labels).item()
                preds = (outputs > 0.5).float()
                val_correct += (preds == labels).sum().item()

        val_acc = val_correct / len(val_ds) * 100

        print(f"Epoch [{epoch+1}/{args.epochs}] "
              f"Train Loss: {train_loss/len(train_loader):.4f} Acc: {train_acc:.2f}% | "
              f"Val Loss: {val_loss/len(val_loader):.4f} Acc: {val_acc:.2f}%")

        writer.add_scalar("Loss/train", train_loss, epoch)
        writer.add_scalar("Loss/val", val_loss, epoch)
        writer.add_scalar("Accuracy/train", train_acc, epoch)
        writer.add_scalar("Accuracy/val", val_acc, epoch)

        # Save best checkpoint
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            ckpt_path = os.path.join(args.checkpoint_dir, f"{args.model}.pth")
            state = model.module.state_dict() if hasattr(model, "module") else model.state_dict()
            torch.save({
                "epoch": epoch,
                "model_state": state,
                "optimizer_state": optimizer.state_dict(),
                "best_val_acc": best_val_acc,
            }, ckpt_path)
            print(f"  ✅ New best checkpoint saved: {ckpt_path} (val_acc={val_acc:.2f}%)")

    writer.close()
    print(f"\nTraining complete. Best Val Accuracy: {best_val_acc:.2f}%")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AuthenticEye Training Pipeline")
    parser.add_argument("--model", type=str, default="efficientnet_b4",
                        choices=["efficientnet_b4", "xceptionnet", "vit"])
    parser.add_argument("--data_dir", type=str, required=True, help="Path to dataset (with train/ and val/ subdirs)")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--checkpoint_dir", type=str, default="../ai-service/checkpoints")
    parser.add_argument("--log_dir", type=str, default="./tensorboard_logs")
    parser.add_argument("--resume", type=str, default=None, help="Path to checkpoint to resume from")
    args = parser.parse_args()
    train_model(args)
