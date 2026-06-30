import os
import sys
import argparse
import subprocess
from pathlib import Path

def run_command(cmd, desc="Running command"):
    print("\n" + "="*80)
    print(f"[RUNNING] {desc}...")
    print(f"Command: {' '.join(cmd)}")
    print("="*80 + "\n")
    
    result = subprocess.run(cmd, stdout=sys.stdout, stderr=sys.stderr)
    if result.returncode != 0:
        print(f"\n[ERROR] Error: command failed with exit code {result.returncode}")
        sys.exit(result.returncode)
    print(f"[SUCCESS] {desc} completed successfully!\n")

def main():
    parser = argparse.ArgumentParser(description="AuthenticEye Colab Master Trainer")
    parser.add_argument("--source_dir", type=str, default="./raw_data", help="Path to raw dataset")
    parser.add_argument("--prepared_dir", type=str, default="./prepared_data", help="Path to prepared dataset output")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of images per class for training")
    parser.add_argument("--epochs_cnn", type=int, default=15, help="Number of training epochs for CNNs")
    parser.add_argument("--epochs_vit", type=int, default=10, help="Number of training epochs for ViT")
    parser.add_argument("--epochs_fusion", type=int, default=50, help="Number of training epochs for Fusion MLP")
    parser.add_argument("--batch_size", type=int, default=32, help="Batch size for training")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate")
    parser.add_argument("--use_amp", action="store_true", default=True, help="Use Automatic Mixed Precision")
    parser.add_argument("--skip_prep", action="store_true", help="Skip dataset preparation split")
    parser.add_argument("--download_kaggle", type=str, default=None, help="Kaggle Dataset name (if downloading)")
    
    args = parser.parse_args()

    # Define paths relative to the script location
    script_dir = Path(__file__).parent.parent.resolve()
    os.chdir(script_dir)
    print(f"Working directory set to: {os.getcwd()}")

    # 1. Dataset Preparation
    if not args.skip_prep:
        prep_cmd = [
            "python", "scripts/prepare_dataset.py",
            "--source", args.source_dir,
            "--dest", args.prepared_dir,
            "--ratio", "0.8"
        ]
        if args.limit:
            prep_cmd += ["--limit", str(args.limit)]
        if args.download_kaggle:
            prep_cmd += ["--download-kaggle", args.download_kaggle]
            
        run_command(prep_cmd, "Dataset Preparation")

    # Ensure checkpoints directory exists
    os.makedirs("./checkpoints", exist_ok=True)

    # 2. Train Base Models
    models_to_train = [
        ("efficientnet_b4", args.epochs_cnn),
        ("xceptionnet", args.epochs_cnn),
        ("vit", args.epochs_vit)
    ]

    for model_name, epochs in models_to_train:
        train_cmd = [
            "python", "training/trainer.py",
            "--model", model_name,
            "--data_dir", args.prepared_dir,
            "--epochs", str(epochs),
            "--batch_size", str(args.batch_size if model_name != "vit" else max(8, args.batch_size // 2)),
            "--lr", str(args.lr if model_name != "vit" else args.lr / 2.0),
            "--checkpoint_dir", "./checkpoints"
        ]
        if args.use_amp:
            train_cmd.append("--use_amp")
            
        run_command(train_cmd, f"Training Base Model: {model_name}")

        # Post-training: Create duplicate checkpoint without the "_best" suffix 
        # to satisfy the load_models standard (e.g. efficientnet_b4.pth)
        best_ckpt = Path(f"./checkpoints/{model_name}_best.pth")
        std_ckpt = Path(f"./checkpoints/{model_name}.pth")
        if best_ckpt.exists():
            import shutil
            shutil.copy2(best_ckpt, std_ckpt)
            print(f"[INFO] Copied standard checkpoint to: {std_ckpt}")

    # 3. Extract Features for Fusion MLP
    ext_cmd = [
        "python", "scripts/extract_features.py",
        "--data_dir", args.prepared_dir,
        "--checkpoints_dir", "./checkpoints",
        "--output_file", "./checkpoints/extracted_features.pt"
    ]
    run_command(ext_cmd, "Extracting features for Fusion MLP training")

    # 4. Train Fusion MLP Meta-Classifier
    fusion_cmd = [
        "python", "fusion/train_fusion.py",
        "--features_file", "./checkpoints/extracted_features.pt",
        "--epochs", str(args.epochs_fusion),
        "--save_path", "./checkpoints/fusion_mlp.pth"
    ]
    run_command(fusion_cmd, "Training Fusion MLP Meta-Classifier")

    print("\n" + "="*80)
    print("[COMPLETE] ALL MODELS TRAINED AND SAVED SUCCESSFULLY!")
    print("Checkpoints saved in 'ai-service/checkpoints/':")
    print("  - efficientnet_b4_best.pth / efficientnet_b4.pth")
    print("  - xceptionnet_best.pth / xceptionnet.pth")
    print("  - vit_best.pth / vit.pth")
    print("  - fusion_mlp.pth")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
