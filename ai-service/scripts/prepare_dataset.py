import os
import shutil
import random
import argparse
import urllib.request
import time
import zipfile
from pathlib import Path
import warnings


def download_kaggle_dataset(source_dir, kaggle_repo):
    """Optional Kaggle dataset downloader"""
    try:
        import kaggle
    except ImportError:
        print("Install kaggle: pip install kaggle")
        print("You must also configure your kaggle.json API token.")
        return False

    print(f"Downloading Kaggle dataset: {kaggle_repo}")
    try:
        kaggle.api.authenticate()
        kaggle.api.dataset_download_files(kaggle_repo, path=source_dir, unzip=True)
        print(f"Dataset extracted to {source_dir}")
        return True
    except Exception as e:
        print(f"Kaggle download failed: {e}")
        return False


def download_sample_dataset(source_dir):
    """Downloads 500 real and 500 fake images."""
    print("Downloading sample dataset...")

    source_dir = Path(source_dir)
    real_dir = source_dir / "real"
    fake_dir = source_dir / "fake"

    real_dir.mkdir(parents=True, exist_ok=True)
    fake_dir.mkdir(parents=True, exist_ok=True)

    # =========================
    # REAL IMAGES (500)
    # =========================
    print("Downloading real images...")

    for i in range(500):
        try:
            url = f"https://source.unsplash.com/512x512/?face&sig={i}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                with open(real_dir / f"real_{i}.jpg", "wb") as f:
                    f.write(response.read())
            time.sleep(0.3)
        except Exception as e:
            print(f"[REAL] Failed {i}: {e}")

    # =========================
    # FAKE IMAGES (500)
    # =========================
    print("Downloading fake (AI-generated) images...")

    for i in range(500):
        try:
            url = f"https://thispersondoesnotexist.com/?t={int(time.time()*1000)}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                with open(fake_dir / f"fake_{i}.jpg", "wb") as f:
                    f.write(response.read())
            time.sleep(1.2)  # avoid blocking
        except Exception as e:
            print(f"[FAKE] Failed {i}: {e}")

    print("Download complete.")


def download_hf_dataset(source_dir, hf_repo):
    """Optional HuggingFace dataset downloader"""
    try:
        from datasets import load_dataset
    except ImportError:
        print("Install datasets: pip install datasets")
        return False

    print(f"Downloading HuggingFace dataset: {hf_repo}")

    try:
        dataset = load_dataset(hf_repo, split='train', streaming=True)

        source_dir = Path(source_dir)
        real_dir = source_dir / "real"
        fake_dir = source_dir / "fake"

        real_dir.mkdir(parents=True, exist_ok=True)
        fake_dir.mkdir(parents=True, exist_ok=True)

        real_count, fake_count = 0, 0
        max_per_class = 500

        for item in dataset:
            image = item.get('image') or item.get('img')
            label = item.get('label') or item.get('target')

            if image is None or label is None:
                continue

            is_fake = False
            if isinstance(label, int):
                is_fake = label == 1
            elif isinstance(label, str):
                is_fake = label.lower() in ["fake", "1", "synthetic"]

            if is_fake and fake_count < max_per_class:
                image.save(fake_dir / f"hf_fake_{fake_count}.jpg")
                fake_count += 1
            elif not is_fake and real_count < max_per_class:
                image.save(real_dir / f"hf_real_{real_count}.jpg")
                real_count += 1

            if real_count >= max_per_class and fake_count >= max_per_class:
                break

        print(f"Downloaded {real_count} real & {fake_count} fake images")
        return True

    except Exception as e:
        print(f"HF download failed: {e}")
        return False


def organize_pre_split_dataset(source_dir, dest_dir, limit=None):
    """
    If the dataset is already split (like many Kaggle datasets),
    just copy/move them to the expected format.
    """
    source = Path(source_dir)
    dest = Path(dest_dir)

    # Common names for splits
    train_aliases = ["train", "training"]
    val_aliases = ["val", "valid", "validation"]
    test_aliases = ["test", "testing"]

    found_pre_split = False

    # Recursively find directories that contain both train and (val or test)
    # We use rglob to find any directory that has 'train' as a child
    potential_train_dirs = list(source.rglob("train")) + list(source.rglob("training"))
    
    for train_path in potential_train_dirs:
        if not train_path.is_dir():
            continue
            
        parent_dir = train_path.parent
        val_path = next((parent_dir / a for a in val_aliases if (parent_dir / a).exists() and (parent_dir / a).is_dir()), None)
        
        # If no val, check test (we can use test as val if needed)
        if not val_path:
            val_path = next((parent_dir / a for a in test_aliases if (parent_dir / a).exists() and (parent_dir / a).is_dir()), None)

        if train_path and val_path:
            found_pre_split = True
            print(f"Found pre-split directories at {parent_dir}")
            
            for split_name, curr_path in [("train", train_path), ("val", val_path)]:
                for cls in ['real', 'fake']:
                    dest_cls_dir = dest / split_name / cls
                    dest_cls_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Sometimes fake faces might be named 'fake' and 'real' or variations
                    # In 140k dataset it's real/fake under the splits
                    curr_cls_path = curr_path / cls
                    if not curr_cls_path.exists():
                        # Try case insensitive match if typical 'real' 'fake' not found
                        for d in curr_path.iterdir():
                            if d.is_dir() and cls in d.name.lower():
                                curr_cls_path = d
                                break
                    
                    if curr_cls_path.exists():
                        images = list(curr_cls_path.rglob("*.jpg")) + list(curr_cls_path.rglob("*.jpeg")) + list(curr_cls_path.rglob("*.png"))
                        
                        # Apply limit proportionally if pre-split
                        if limit is not None:
                            if split_name == "train":
                                split_limit = int(limit * 0.8) # Default ratio
                            else:
                                split_limit = int(limit * 0.2)
                            images = images[:split_limit]
                            
                        print(f"Copying {len(images)} images for {split_name}/{cls} ...")
                        for img in images:
                            shutil.copy2(img, dest_cls_dir / img.name)
            break
            
    return found_pre_split


def split_dataset(source_dir, dest_dir, split_ratio=0.8, limit=None):
    """Splits dataset into train/val"""

    if organize_pre_split_dataset(source_dir, dest_dir, limit):
        print("Using pre-split dataset organization.")
        return

    source = Path(source_dir)
    dest = Path(dest_dir)

    for cls in ['real', 'fake']:
        cls_path = source / cls

        if not cls_path.exists():
            print(f"Missing basic '{cls}' folder for generic splitting at: {cls_path}")
            continue

        images = []
        for ext in ["*.jpg", "*.png", "*.jpeg", "*.JPG", "*.PNG"]:
            images.extend(list(cls_path.rglob(ext)))

        if not images:
            print(f"No images in {cls_path}")
            continue

        random.shuffle(images)
        if limit is not None:
            images = images[:limit]
        split_idx = int(len(images) * split_ratio)

        train_imgs = images[:split_idx]
        val_imgs = images[split_idx:]

        train_dir = dest / "train" / cls
        val_dir = dest / "val" / cls

        train_dir.mkdir(parents=True, exist_ok=True)
        val_dir.mkdir(parents=True, exist_ok=True)

        print(f"{cls.upper()} → Train: {len(train_imgs)} | Val: {len(val_imgs)}")

        for img in train_imgs:
            shutil.copy2(img, train_dir / img.name)

        for img in val_imgs:
            shutil.copy2(img, val_dir / img.name)


def unzip_dataset(zip_path, extract_to):
    """Unzips the dataset to the specified directory."""
    print(f"Extracting {zip_path} to {extract_to}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    print("Extraction complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--source", type=str, required=True)
    parser.add_argument("--dest", type=str, default="./prepared_data")
    parser.add_argument("--ratio", type=float, default=0.8)

    parser.add_argument("--download-sample", action="store_true")
    parser.add_argument("--download-hf", type=str, default=None)
    parser.add_argument("--download-kaggle", type=str, default=None, help="Kaggle dataset ID, e.g., 'xhlulu/140k-real-and-fake-faces'")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of images to process per class")

    args = parser.parse_args()

    if args.download_sample:
        download_sample_dataset(args.source)

    if args.download_hf:
        download_hf_dataset(args.source, args.download_hf)

    if args.download_kaggle:
        download_kaggle_dataset(args.source, args.download_kaggle)

    source_path = Path(args.source)
    if source_path.suffix == ".zip":
        zip_path = source_path
        extract_to = source_path.parent / source_path.stem
        if not extract_to.exists():
            unzip_dataset(zip_path, extract_to)
        args.source = str(extract_to)

    split_dataset(args.source, args.dest, args.ratio, args.limit)

    print("Dataset ready for training!")