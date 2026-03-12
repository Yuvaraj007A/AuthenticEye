"""
AuthenticEye — Quick Training Runner (CPU-friendly)
===================================================
1. Generates synthetic dataset  (real vs. GAN-artifact fake images)
2. Trains EfficientNet-B4, XceptionNet, and ViT
3. Saves checkpoints to ai-service/checkpoints/

Usage:
    python training/run_training.py

Takes ~20-60 min on CPU depending on machine speed.
Use --epochs 5 for a quick smoke test.
"""
import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
TRAINING_DIR = ROOT / "training"
DATA_DIR = ROOT / "training" / "data"
CHECKPOINT_DIR = ROOT / "ai-service" / "checkpoints"
VENV_PYTHON = ROOT / "ai-service" / "venv" / "Scripts" / "python.exe"

def run(cmd, cwd=None):
    print(f"\n$ {' '.join(str(c) for c in cmd)}\n")
    result = subprocess.run(cmd, cwd=cwd or ROOT)
    if result.returncode != 0:
        print(f"⚠️  Command returned {result.returncode} — continuing...")
    return result.returncode

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=500,
                        help="Images per class for dataset (default 500; use 200 for quick test)")
    parser.add_argument("--epochs", type=int, default=10,
                        help="Training epochs per model (default 10)")
    parser.add_argument("--batch_size", type=int, default=8,
                        help="Batch size (default 8 for CPU)")
    parser.add_argument("--lr", type=float, default=5e-5)
    parser.add_argument("--models", nargs="+",
                        default=["efficientnet_b4", "xceptionnet", "vit"],
                        help="Which models to train")
    args = parser.parse_args()

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Step 1: Generate dataset ─────────────────────────────────────────────
    print("=" * 60)
    print("STEP 1: Generating synthetic training dataset")
    print("=" * 60)
    run([
        str(VENV_PYTHON),
        str(TRAINING_DIR / "generate_synthetic_dataset.py"),
        "--out_dir", str(DATA_DIR),
        "--count", str(args.count),
    ])

    # ── Step 2: Train each model ──────────────────────────────────────────────
    for model_name in args.models:
        print("\n" + "=" * 60)
        print(f"STEP 2: Training {model_name}")
        print("=" * 60)
        run([
            str(VENV_PYTHON),
            str(TRAINING_DIR / "train.py"),
            "--model", model_name,
            "--data_dir", str(DATA_DIR),
            "--epochs", str(args.epochs),
            "--batch_size", str(args.batch_size),
            "--lr", str(args.lr),
            "--checkpoint_dir", str(CHECKPOINT_DIR),
        ])

        ckpt = CHECKPOINT_DIR / f"{model_name}.pth"
        if ckpt.exists():
            size_mb = ckpt.stat().st_size / 1024 / 1024
            print(f"\n  ✅ Checkpoint saved: {ckpt}  ({size_mb:.1f} MB)")
        else:
            print(f"\n  ⚠️  No checkpoint found for {model_name}. Check training output above.")

    print("\n" + "=" * 60)
    print("✅ ALL TRAINING COMPLETE")
    print(f"   Checkpoints saved to: {CHECKPOINT_DIR}")
    print("   Restart the AI service to load new weights:")
    print("   ai-service\\venv\\Scripts\\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000")
    print("=" * 60)
