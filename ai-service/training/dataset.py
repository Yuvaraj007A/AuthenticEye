import os
from pathlib import Path
from PIL import Image
import numpy as np
import torch
from torch.utils.data import Dataset, WeightedRandomSampler
import albumentations as A
from albumentations.pytorch import ToTensorV2

# ─── Augmentation ─────────────────────────────────────────────────────────────

# Train transform with heavy real-world degradation simulation
train_transform = A.Compose([
    A.Resize(height=256, width=256),
    A.RandomCrop(height=224, width=224),
    A.HorizontalFlip(p=0.5),
    A.ImageCompression(quality_lower=40, quality_upper=100, p=0.3), # JPEG compression
    A.GaussianBlur(blur_limit=(3, 7), p=0.2), # Blur
    A.GaussNoise(var_limit=(10.0, 50.0), p=0.2), # Noise
    A.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1, p=0.5),
    A.ShiftScaleRotate(shift_limit=0.0625, scale_limit=0.1, rotate_limit=15, p=0.5),
    A.ToGray(p=0.05),
    A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ToTensorV2(),
])

# Validation transform
val_transform = A.Compose([
    A.Resize(height=224, width=224),
    A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ToTensorV2(),
])

# ─── Dataset ─────────────────────────────────────────────────────────────────

class DeepfakeDataset(Dataset):
    """
    Universal deepfake dataset loader with albumentations support.
    Expects folder structure:
      data/
        real/  ← authentic images
        fake/  ← deepfake images
    """
    def __init__(self, root_dir: str, transform=None):
        self.samples = []
        self.transform = transform
        self.labels_list = []

        real_dir = Path(root_dir) / "real"
        fake_dir = Path(root_dir) / "fake"

        # Load real images
        if real_dir.exists():
            for ext in ["**/*.jpg", "**/*.png", "**/*.jpeg"]:
                for img_path in real_dir.glob(ext):
                    self.samples.append((str(img_path), 0.0))
                    self.labels_list.append(0)
                    
        # Load fake images
        if fake_dir.exists():
            for ext in ["**/*.jpg", "**/*.png", "**/*.jpeg"]:
                for img_path in fake_dir.glob(ext):
                    self.samples.append((str(img_path), 1.0))
                    self.labels_list.append(1)

        print(f"Dataset loaded from {root_dir}: {len(self.samples)} samples "
              f"({sum(1 for l in self.labels_list if l==0)} real, "
              f"{sum(1 for l in self.labels_list if l==1)} fake)")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        image = Image.open(img_path).convert("RGB")
        image_np = np.array(image)

        if self.transform:
            augmented = self.transform(image=image_np)
            image_tensor = augmented['image']
        else:
            # Fallback to simple tensor conversion if no transform
            image_tensor = torch.from_numpy(image_np.transpose((2, 0, 1))).float() / 255.0

        return image_tensor, torch.tensor(label, dtype=torch.float32)

def get_balanced_sampler(dataset: DeepfakeDataset):
    """
    Returns a WeightedRandomSampler to handle class imbalance.
    """
    labels = np.array(dataset.labels_list)
    class_sample_count = np.array([len(np.where(labels == t)[0]) for t in np.unique(labels)])
    
    # Avoid division by zero if a class is entirely missing
    if 0 in class_sample_count:
        print("Warning: One or more classes have 0 samples. Sampler may misbehave.")
        weight = np.ones(len(labels))
    else:
        weight = 1. / class_sample_count
        
    samples_weight = np.array([weight[t] for t in labels])
    samples_weight = torch.from_numpy(samples_weight).float()
    
    sampler = WeightedRandomSampler(samples_weight, len(samples_weight), replacement=True)
    return sampler
