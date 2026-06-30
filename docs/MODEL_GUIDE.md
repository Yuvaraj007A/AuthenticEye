# AuthenticEye Platform — AI Models & Ensemble Architecture Guide

This guide details the deep learning models, feature extraction pipelines, and machine learning ensemble classifier used for deepfake detection in AuthenticEye.

---

## 1. Ensemble Architecture Overview

AuthenticEye implements a **stacking ensemble architecture** using a Logistic Regression model as the meta-classifier. Instead of relying on raw neural logits or hardcoded fusion blend weights, the platform extracts high-level prediction probabilities and signal artifacts, feeding them as features to the meta-model.

```
                  ┌──────────────────────┐
                  │   Input Cropped Face │
                  └──────────┬───────────┘
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ EfficientNet-B4 │ │   XceptionNet   │ │  FFT frequency  │
│  (Spatial CNN)  │ │  (Texture CNN)  │ │   (Spectrum)    │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         └─────────┐         │         ┌─────────┘
                   ▼         ▼         ▼
               ┌───────────────────────────┐
               │    Artifact statistics    │
               │    (Fourier Residuals)    │
               └─────────────┬─────────────┘
                             ▼
               ┌───────────────────────────┐
               │ Logistic Reg. Ensemble    │
               │ (Fitted Meta-Classifier)  │
               └─────────────┬─────────────┘
                             ▼
                  ┌──────────────────────┐
                  │ Real vs Fake Decision │
                  └──────────────────────┘
```

---

## 2. Classifier Component Details

### A. EfficientNet-B4 (Spatial Feature Extractor)
- **Primary Focus**: High-level semantic features, facial distortions, lighting inconsistencies, structural irregularities.
- **Model Base**: `efficientnet_b4` fine-tuned using binary cross-entropy loss.
- **Target Weights**: `models/efficientnet_dfdc.pt` (trained on DFDC dataset).

### B. XceptionNet (Texture & Pattern Extractor)
- **Primary Focus**: Fine-grained pixel textures, artificial boundaries, blending artifacts, color-space transitions.
- **Model Base**: Fine-tuned XceptionNet classifier.
- **Target Weights**: `models/xception_ffpp.pt` (trained on FaceForensics++ dataset).

### C. FFT Frequency Detector (Spectral Analysis)
- **Primary Focus**: Anomalous high-frequency power residuals in the Fourier domain. Synthetic generators (GANs, Diffusion models) leave periodic, checkerboard, or grid artifact fingerprints.
- **Implementation**: Computes a 2D Fast Fourier Transform on the grayscale face crop, azimuthally integrates the power spectrum to construct a 1D radial power profile, and matches power coefficients against standard real face profiles to derive a probability score.

### D. Artifact Detector (Reconstruction Statistics)
- **Primary Focus**: Blending boundaries, edge pixel noise gradients, color discrepancies.
- **Implementation**: Computes local entropy statistics and edge variances across the RGB face region to capture structural consistency markers.

---

## 3. Ensemble Fusion via Logistic Regression

The feature vector $\mathbf{x}$ fed into the Logistic Regression model is defined as:
$$\mathbf{x} = \begin{bmatrix} p_{\text{eff}} & p_{\text{xcep}} & p_{\text{fft}} & p_{\text{artifact}} \end{bmatrix}$$

where:
- $p_{\text{eff}}$ = Probability score from EfficientNet-B4
- $p_{\text{xcep}}$ = Probability score from XceptionNet
- $p_{\text{fft}}$ = High-frequency signal anomaly score
- $p_{\text{artifact}}$ = Texture artifact score

The meta-classifier computes the final probability of deepfake origin:
$$P(\text{fake} \mid \mathbf{x}) = \sigma(\mathbf{w}^T \mathbf{x} + b)$$

where $\sigma(z) = \frac{1}{1 + e^{-z}}$, $\mathbf{w}$ represents the fitted coefficients, and $b$ is the intercept. These weights are serialized and loaded dynamically from `models/ensemble.pkl`.
