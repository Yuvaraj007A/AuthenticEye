import os
import sys
import argparse
import torch
from PIL import Image
from tqdm import tqdm
from pathlib import Path

# Add root folder to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from inference.pipeline import AuthenticEyePipeline

def main(args_list=None):
    parser = argparse.ArgumentParser(description="Extract forensic features from dataset for Fusion MLP training")
    parser.add_argument("--data_dir", type=str, required=True, help="Path to prepared dataset directory containing train/val")
    parser.add_argument("--checkpoints_dir", type=str, default="./checkpoints", help="Path to trained base model checkpoints")
    parser.add_argument("--output_file", type=str, default="extracted_features.pt", help="Path to save the extracted features")
    args = parser.parse_args(args_list)

    # Initialize the pipeline
    pipeline = AuthenticEyePipeline(checkpoints_dir=args.checkpoints_dir)

    features_list = []
    labels_list = []

    print(f"Scanning dataset from: {args.data_dir}")

    # Traverse through train and val splits, and real/fake classes
    data_path = Path(args.data_dir)
    image_paths = []
    
    for split in ["train", "val"]:
        split_dir = data_path / split
        if not split_dir.exists():
            continue
        for label_name, label_val in [("real", 0.0), ("fake", 1.0)]:
            class_dir = split_dir / label_name
            if not class_dir.exists():
                continue
            for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]:
                for img_path in class_dir.glob(ext):
                    image_paths.append((img_path, label_val))

    if not image_paths:
        print("❌ No images found in the dataset directory. Please verify paths.")
        sys.exit(1)

    print(f"Found {len(image_paths)} images. Commencing feature extraction...")

    for img_path, label in tqdm(image_paths, desc="Extracting features"):
        try:
            with Image.open(img_path) as img:
                img = img.convert("RGB")
                # Extract 16-dim feature vector
                feats = pipeline.extract_features(img)
                features_list.append(feats)
                labels_list.append([label])
        except Exception as e:
            print(f"⚠️ Warning: Failed to extract features for {img_path}: {e}")

    # Convert to PyTorch tensors and save
    features_tensor = torch.FloatTensor(features_list)
    labels_tensor = torch.FloatTensor(labels_list)

    print(f"Extracted feature tensor shape: {features_tensor.shape}")
    print(f"Extracted labels tensor shape: {labels_tensor.shape}")

    torch.save({
        "features": features_tensor,
        "labels": labels_tensor
    }, args.output_file)

    print(f"✅ Features saved successfully to {args.output_file}")

if __name__ == "__main__":
    main()
