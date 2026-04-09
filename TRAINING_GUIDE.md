# AuthenticEye v5.0 Training Guide

Training the AuthenticEye Forensic Suite is a multi-step process. The system uses a cascaded architecture where you first train the heavy base models (EfficientNet, XceptionNet, ViT) on raw deepfake datasets, then extract their outputs alongside physics-based signals to train the final Meta-Fusion classifier.

---

## Step 1: Prepare Your Dataset
Before training, you need to structure your incoming raw dataset.
1. Place all your baseline authentic media into a folder called `real/` and manipulated media into `fake/` inside a source directory.
2. Navigate to the AI service:
   ```bash
   cd ai-service
   ```
3. Run the dataset preparation script. This will automatically randomize, split (80/20 train-val), and construct the proper folder hierarchy:
   ```bash
   python scripts/prepare_dataset.py --source /path/to/raw_dataset --dest ./prepared_data --ratio 0.8
   ```

---

## Step 2: Train the Base Foundation Models
The system relies on three parallel core models. You can train them individually using the main `trainer.py` script. The script automatically handles Automatic Mixed Precision (AMP), gradient clipping, class-balancing samplers, and focal loss.

From the `ai-service` directory, run:

### Train EfficientNet-B4
```bash
python training/trainer.py \
    --model efficientnet_b4 \
    --data_dir ./prepared_data \
    --epochs 50 \
    --batch_size 32 \
    --lr 1e-4 \
    --loss focal \
    --use_amp
```

### Train XceptionNet
```bash
python training/trainer.py \
    --model xceptionnet \
    --data_dir ./prepared_data \
    --epochs 50 \
    --batch_size 32 \
    --lr 1e-4 \
    --use_amp
```

### Train Vision Transformer (ViT)
```bash
python training/trainer.py \
    --model vit \
    --data_dir ./prepared_data \
    --epochs 30 \
    --batch_size 16 \
    --lr 5e-5 \
    --use_amp
```

> **Checkpoints**: The best-performing weights (`val_auc` based) will automatically be saved to `ai-service/checkpoints/` as `<model>_best.pth`. Logs are exported to `tensorboard_logs/`.

---

## Step 3: Train the Fusion Meta-Classifier
Once the base CNN/ViT models are trained, they act as sophisticated feature extractors. The overarching Multi-Layer Perceptron (MLP) learns how to weigh their outputs against physics-based extractions (GAN fingerprints, Diffusion traces, Frequency maps).

1. First, you must pass your dataset through the `extract_features()` method in `pipeline.py` to cache a `.pt` file of the `(16-dim)` vectors for your dataset.
2. Once you have `extracted_features.pt`, navigate to the fusion directory and train the MLP meta-classifier:
   ```bash
   cd fusion
   python train_fusion.py --features_file extracted_features.pt --epochs 50 --save_path ../checkpoints/fusion_mlp.pth
   ```

*Note: If `extracted_features.pt` is missing, `train_fusion.py` will generate randomized dummy matrices to verify the training code executes cleanly.*
