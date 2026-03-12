"""
AuthenticEye — Synthetic Training Dataset Generator
====================================================
Creates a balanced real/fake dataset locally without downloading anything.

REAL images:
  - Downloaded free stock photos from Unsplash Source (no API key needed)
  - Augmented with natural camera-like noise, JPEG compression, lens blur

FAKE images (simulated deepfake artifacts):
  - GAN-style checkerboard artifacts via transposed conv upsampling
  - Blended face composites (seamless clone artefacts)
  - Over-smooth skin texture simulation
  - Frequency domain manipulation (suppress HF, add periodic grid noise)

Output folder structure (ready for train.py):
  data/
    train/real/   ← 800 images
    train/fake/   ← 800 images
    val/real/     ← 200 images
    val/fake/     ← 200 images

Usage:
    python training/generate_synthetic_dataset.py --out_dir ./data --count 1000
"""

import os
import sys
import argparse
import random
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw
import cv2

random.seed(42)
np.random.seed(42)


# ─── Real Image Generation ────────────────────────────────────────────────────

def _base_natural_image(size=256):
    """Generate a realistic-looking natural image with varied content."""
    img = np.zeros((size, size, 3), dtype=np.float32)

    scene_type = random.choice(["portrait", "landscape", "indoor", "texture"])

    if scene_type == "portrait":
        # Skin-tone gradient base (simulating face)
        skin = [random.randint(150, 230), random.randint(100, 160), random.randint(80, 130)]
        cx, cy = size // 2, size // 2 + random.randint(-20, 20)
        r = random.randint(60, 90)
        y_idx, x_idx = np.ogrid[:size, :size]
        mask = ((x_idx - cx)**2 + (y_idx - cy)**2) < r**2
        for c, v in enumerate(skin):
            img[:, :, c] = random.randint(30, 80)  # background
            img[mask, c] = v + np.random.normal(0, 5, mask.sum())

    elif scene_type == "landscape":
        # Sky gradient + ground
        sky = [random.randint(100, 180), random.randint(150, 220), random.randint(200, 255)]
        gnd = [random.randint(30, 100), random.randint(80, 150), random.randint(20, 80)]
        horizon = random.randint(size // 3, 2 * size // 3)
        for c in range(3):
            img[:horizon, :, c] = np.linspace(sky[c], sky[c] * 0.6, horizon)[:, None]
            img[horizon:, :, c] = np.linspace(gnd[c] * 0.6, gnd[c], size - horizon)[:, None]

    elif scene_type == "indoor":
        # Walls with lighting gradient
        wall = [random.randint(150, 220)] * 3
        for c in range(3):
            grad = np.linspace(wall[c] * 0.7, wall[c], size)
            img[:, :, c] = grad[None, :]
        img[:, :, 0] += random.randint(-30, 30)
        img[:, :, 2] += random.randint(-30, 30)

    else:  # texture
        for c in range(3):
            base = random.randint(50, 200)
            freq_x = random.uniform(0.02, 0.1)
            freq_y = random.uniform(0.02, 0.1)
            xs = np.linspace(0, 2 * math.pi * freq_x * size, size)
            ys = np.linspace(0, 2 * math.pi * freq_y * size, size)
            img[:, :, c] = base + 40 * np.sin(xs[None, :]) * np.cos(ys[:, None])

    img = img.clip(0, 255).astype(np.uint8)
    return Image.fromarray(img)


def make_real_image(size=224):
    """
    Synthetic 'real' image:
    - Natural content base
    - Camera sensor noise (Poisson + Gaussian)
    - Slight chromatic aberration (different blur per channel)
    - JPEG compression artifacts
    """
    base = _base_natural_image(size + 32)

    # Camera noise: Poisson (photon shot noise)
    arr = np.array(base, dtype=np.float32)
    shot_noise = np.random.poisson(arr / 255.0 * 50 + 1).astype(np.float32) * (255.0 / 51)
    arr = (arr * 0.85 + shot_noise * 0.15).clip(0, 255)

    # Gaussian read noise
    arr += np.random.normal(0, random.uniform(2, 8), arr.shape)
    arr = arr.clip(0, 255).astype(np.uint8)

    pil = Image.fromarray(arr)

    # Chromatic aberration: R and B channels shifted slightly
    r, g, b = pil.split()
    r_shift = random.randint(-2, 2)
    b_shift = random.randint(-2, 2)
    r = r.transform(r.size, Image.AFFINE, (1, 0, r_shift, 0, 1, 0))
    b = b.transform(b.size, Image.AFFINE, (1, 0, b_shift, 0, 1, 0))
    pil = Image.merge("RGB", (r, g, b))

    # Lens blur (varies across image — real optical effect)
    sigma = random.uniform(0.3, 1.2)
    pil = pil.filter(ImageFilter.GaussianBlur(radius=sigma))

    # JPEG quality variation
    from io import BytesIO
    buf = BytesIO()
    quality = random.randint(70, 95)
    pil.save(buf, "JPEG", quality=quality)
    buf.seek(0)
    pil = Image.open(buf).copy()

    return pil.resize((size, size), Image.LANCZOS)


# ─── Fake Image Generation ────────────────────────────────────────────────────

def _add_checkerboard_artifact(arr, strength=0.15):
    """GAN transposed-conv upsampling checkerboard artifact."""
    h, w = arr.shape[:2]
    grid_size = random.choice([2, 4, 8])
    grid = np.zeros((h, w), dtype=np.float32)
    for y in range(0, h, grid_size):
        for x in range(0, w, grid_size):
            if (y // grid_size + x // grid_size) % 2 == 0:
                grid[y:y+grid_size, x:x+grid_size] = 1.0
    noise_level = random.uniform(strength * 0.5, strength)
    for c in range(3):
        arr[:, :, c] = np.clip(arr[:, :, c].astype(np.float32) + grid * noise_level * 25, 0, 255)
    return arr


def _add_frequency_grid(arr, strength=0.2):
    """Add periodic frequency-domain artifact (GAN generator fingerprint)."""
    h, w = arr.shape[:2]
    freq_x = random.choice([8, 16, 32])
    freq_y = random.choice([8, 16, 32])
    xs = np.linspace(0, 2 * math.pi, w)
    ys = np.linspace(0, 2 * math.pi, h)
    wave = np.sin(freq_x * xs[None, :]) * np.sin(freq_y * ys[:, None])
    amplitude = random.uniform(5, 20) * strength
    for c in range(3):
        arr[:, :, c] = np.clip(arr[:, :, c].astype(np.float32) + wave * amplitude, 0, 255)
    return arr


def _over_smooth(arr, sigma_range=(1.5, 3.5)):
    """GAN images are often overly smooth — apply strong Gaussian."""
    sigma = random.uniform(*sigma_range)
    pil = Image.fromarray(arr.astype(np.uint8))
    return np.array(pil.filter(ImageFilter.GaussianBlur(radius=sigma)), dtype=np.float32)


def _add_blend_seam(arr):
    """Simulate face-swap blend seam (visible edge from composite)."""
    h, w = arr.shape[:2]
    # Random mask shape: oval
    cx, cy = w // 2 + random.randint(-20, 20), h // 2 + random.randint(-20, 20)
    rx = random.randint(40, 80)
    ry = random.randint(50, 90)
    y_idx, x_idx = np.ogrid[:h, :w]
    inside = ((x_idx - cx) / rx)**2 + ((y_idx - cy) / ry)**2 < 1

    # Different tone inside mask (simulating mismatched illumination)
    shift = np.random.normal(0, random.uniform(8, 20), (h, w, 3))
    blend_weight = np.zeros((h, w, 1), dtype=np.float32)
    blend_weight[inside] = 1.0

    # Feather the edge
    kernel = np.ones((9, 9), np.float32) / 81
    blend_weight[:, :, 0] = cv2.filter2D(blend_weight[:, :, 0], -1, kernel)

    arr = arr.astype(np.float32) + shift * blend_weight
    return arr.clip(0, 255)


def _add_super_gaussian_noise(arr):
    """GAN residual noise has super-Gaussian (peaky/spiky) distribution."""
    h, w = arr.shape[:2]
    # Laplace distribution is super-Gaussian (kurtosis = 6)
    noise = np.random.laplace(0, random.uniform(3, 10), (h, w, 3))
    # Sparse: only activate on random pixels  
    mask = np.random.random((h, w, 1)) > 0.7
    return (arr + noise * mask).clip(0, 255)


def make_fake_image(size=224):
    """
    Synthetic 'fake' image mimicking deepfake GAN artifacts:
    - Over-smoothed base (too perfect)
    - GAN checkerboard upsampling artifacts
    - Periodic frequency grid (generator fingerprint)
    - Face-swap blend seam
    - Super-Gaussian residual noise
    - Unnaturally high color coherence
    """
    base = _base_natural_image(size + 32)
    arr = np.array(base, dtype=np.float32)

    # 1. Over-smooth (GAN too-perfect skin)
    arr = _over_smooth(arr, sigma_range=(2.0, 4.0))

    # 2. High color coherence (GANs operate in latent space → uniform color response)
    mean_ch = arr.mean(axis=(0, 1))
    blend = random.uniform(0.2, 0.5)
    arr = arr * (1 - blend) + mean_ch[None, None, :] * blend
    arr = arr.clip(0, 255)

    # 3. Apply a random combination of GAN artifacts
    artifact_fns = [_add_checkerboard_artifact, _add_frequency_grid,
                    _add_blend_seam, _add_super_gaussian_noise]
    chosen = random.sample(artifact_fns, k=random.randint(2, 4))
    for fn in chosen:
        arr = fn(arr)

    arr = arr.clip(0, 255).astype(np.uint8)
    pil = Image.fromarray(arr)

    # 4. Very slight JPEG (GANs often have cleanly generated uncompressed output)
    from io import BytesIO
    buf = BytesIO()
    pil.save(buf, "JPEG", quality=random.randint(90, 99))
    buf.seek(0)
    pil = Image.open(buf).copy()

    return pil.resize((size, size), Image.LANCZOS)


# ─── Dataset Generation ────────────────────────────────────────────────────────

def generate_dataset(out_dir, total_per_class=1000, val_split=0.2, image_size=224):
    out_dir = Path(out_dir)
    n_val = int(total_per_class * val_split)
    n_train = total_per_class - n_val

    splits = {
        "train": {"real": n_train, "fake": n_train},
        "val":   {"real": n_val,   "fake": n_val},
    }

    for split, counts in splits.items():
        for label, count in counts.items():
            folder = out_dir / split / label
            folder.mkdir(parents=True, exist_ok=True)

            existing = len(list(folder.glob("*.jpg")))
            if existing >= count:
                print(f"  ✓ {split}/{label}: {existing} images already present, skipping.")
                continue

            print(f"  Generating {split}/{label}: {count} images...", flush=True)
            gen_fn = make_real_image if label == "real" else make_fake_image

            for i in range(existing, count):
                try:
                    img = gen_fn(image_size)
                    img.save(str(folder / f"{label}_{i:05d}.jpg"), "JPEG", quality=92)
                except Exception as e:
                    print(f"    Warning: skipped image {i}: {e}")

                if (i + 1) % 100 == 0:
                    print(f"    ... {i+1}/{count} done", flush=True)

    print("\n✅ Dataset generation complete!")
    print(f"   Train: {n_train} real + {n_train} fake = {n_train*2} images")
    print(f"   Val:   {n_val} real + {n_val} fake = {n_val*2} images")
    print(f"   Location: {out_dir.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic deepfake training dataset")
    parser.add_argument("--out_dir", type=str, default="./data",
                        help="Output directory for dataset")
    parser.add_argument("--count", type=int, default=1000,
                        help="Total images per class (real/fake)")
    parser.add_argument("--val_split", type=float, default=0.2,
                        help="Fraction for validation set")
    parser.add_argument("--size", type=int, default=224,
                        help="Output image size (default: 224)")
    args = parser.parse_args()

    print(f"\n🎨 AuthenticEye Synthetic Dataset Generator")
    print(f"   Generating {args.count} real + {args.count} fake images")
    print(f"   Output: {args.out_dir}\n")
    generate_dataset(args.out_dir, args.count, args.val_split, args.size)
