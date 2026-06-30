# AuthenticEye Fine-Tuning Guide

This project has three AI layers:

1. Base image models: EfficientNet-B4, Xception, and ViT.
2. Forensic signal extractors: frequency, GAN fingerprint, and diffusion statistics.
3. Fusion model: a small MLP that learns how to combine model outputs and forensic features.

For best results, fine-tune the base models first, then train the fusion model.

## 1. Prepare Data

Create a raw dataset with this structure:

```text
raw_dataset/
  real/
  fake/
```

Use real photos/videos from the same kind of users you expect in production. Use fake samples from multiple sources: face swaps, GAN faces, Stable Diffusion, Midjourney, DALL-E, low-quality compressed images, and social-media screenshots.

From the repo root:

```powershell
cd ai-service
python scripts/prepare_dataset.py --source C:\path\to\raw_dataset --dest .\training\prepared_data --ratio 0.8
```

The output should become:

```text
ai-service/training/prepared_data/
  train/
    real/
    fake/
  val/
    real/
    fake/
```

## 2. Train Base Models

Start with EfficientNet. It is the best speed/quality tradeoff for this app.

```powershell
python training/trainer.py --model efficientnet_b4 --data_dir .\training\prepared_data --epochs 30 --batch_size 16 --lr 1e-4 --loss focal --use_amp --checkpoint_dir .\checkpoints
```

Then train Xception and ViT if your machine has enough GPU memory:

```powershell
python training/trainer.py --model xceptionnet --data_dir .\training\prepared_data --epochs 30 --batch_size 16 --lr 1e-4 --loss focal --use_amp --checkpoint_dir .\checkpoints
python training/trainer.py --model vit --data_dir .\training\prepared_data --epochs 20 --batch_size 8 --lr 5e-5 --loss focal --use_amp --checkpoint_dir .\checkpoints
```

The trainer now saves both names automatically:

```text
checkpoints/efficientnet_b4_best.pth
checkpoints/efficientnet_b4.pth
checkpoints/xceptionnet_best.pth
checkpoints/xceptionnet.pth
checkpoints/vit_best.pth
checkpoints/vit.pth
```

The live FastAPI service loads these automatically.

If `checkpoints/fusion_mlp.pth` exists and loads successfully, the image API uses the trained fusion model as the final score. If it is missing or fails to load, the API falls back to the fixed forensic blend and returns `scoring_method: "fixed_forensic_blend"`.

## 3. Train Fusion Model

After base model training, extract the 16-dimensional feature vectors:

```powershell
python scripts/extract_features.py --data_dir .\training\prepared_data --checkpoints_dir .\checkpoints --output_file .\extracted_features.pt
```

Then train the fusion MLP:

```powershell
cd fusion
python train_fusion.py --features_file ..\extracted_features.pt --epochs 50 --save_path ..\checkpoints\fusion_mlp.pth
cd ..
```

Do not train fusion without `extracted_features.pt`. The script now blocks dummy-data training.

## 4. Feedback Retraining

The admin dashboard can verify user corrections and copy them into:

```text
ai-service/training/verified_data/
  real/
  fake/
```

When retraining is triggered, the service fine-tunes EfficientNet on the prepared dataset plus verified feedback. This is useful for small production corrections, not a replacement for full base-model and fusion retraining.

## 5. Deployment Check

Restart the AI service after training:

```powershell
uvicorn main:app --host 0.0.0.0 --port 8000
```

Watch startup logs. You want to see checkpoint-loaded messages for each model, not ImageNet fallback warnings.

## 6. What Metrics To Trust

Use validation AUC and F1 first. Accuracy alone can lie if the dataset is imbalanced.

Good deployment targets:

- AUC: 0.90 or higher on a held-out validation set.
- F1: 0.85 or higher.
- False positive rate: low enough that real users are not frequently accused.
- Test performance on compressed, cropped, resized, and screenshot images.

If AUC is high but real images are frequently flagged fake, reduce threshold sensitivity or add more hard real negatives.
