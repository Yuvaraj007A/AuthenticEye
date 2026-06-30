# AuthenticEye Platform — Adaptive Learning & MLOps Guide

This document describes the design of the Feedback-Driven Adaptive Learning System, model retraining triggers, version registries, and rollbacks.

---

## 1. Feedback Correction Cycle

AuthenticEye implements an MLOps loop that updates the ensemble models dynamically based on verified user feedback:

```
                  ┌───────────────────────┐
                  │ System Predicts Score │
                  └──────────┬────────────┘
                             │
                             ▼
                  ┌───────────────────────┐
                  │ User Flags Correction │
                  │ (Real/Fake Discrep.)  │
                  └──────────┬────────────┘
                             │
                             ▼
                  ┌───────────────────────┐
                  │   Feedback Queue      │
                  │   (status: pending)   │
                  └──────────┬────────────┘
                             │
                 Admin Audited Verification
                             │
                             ▼
                  ┌───────────────────────┐
                  │ VerifiedRetrainFolder │
                  │ (status: verified)    │
                  └──────────┬────────────┘
                             │
                  Admin Triggers Retraining
                             │
                             ▼
                  ┌───────────────────────┐
                  │ Fit Logistic Ensemble │
                  │ (Promote to v2 / v3)  │
                  └───────────────────────┘
```

1. **Submission**: Users can flag any scanned image using the **Submit Correction** trigger if they suspect the model's classification is wrong.
2. **Review**: The input is stored in MongoDB as a `Feedback` document with `status: 'pending'`.
3. **Audit**: Administrators review the feedback queue in the Admin Dashboard.
4. **Verification Action**:
   - The administrator validates the input as either `real` or `fake`.
   - The verified image is copied from `/uploads/` to two directories:
     - `ai-service/training/verified_data/<real|fake>/` (consumed by the Python training script).
     - `feedback_dataset/verified_dataset/<real|fake>/` (permanent archive directory).

---

## 2. Automated Model Retraining Pipeline

When there are pending verified samples in the feedback registry:
1. The Admin clicks **Trigger Automated Retraining**.
2. The backend sends a request to FastAPI `/retrain`.
3. The retraining manager (`ai-service/training/retrain_manager.py`):
   - Extracts CNN logit and signal artifact features from the original prepared training data + the newly accumulated `verified_data/` images.
   - Refits the Logistic Regression ensemble classifier model.
   - Computes accuracy, precision, recall, and F1 score on the validation split.
   - Creates a new version directory checkpoint (e.g., `models/v2/`, `models/v3/`) and writes a performance summary JSON file (`metadata.json`).
   - Reloads the newly trained model weights in the active serving process.

---

## 3. Directory Versioning & Rollback Strategy

The AI microservice maintains a version rotation registry under the `ai-service/models/` folder:

- **Active Directory**: The files `efficientnet_dfdc.pt`, `xception_ffpp.pt`, `ensemble.pkl`, and `current.json` in the root of the `models/` directory represent the active model version.
- **Version Checkpoints (`v1`, `v2`, `v3`)**: Each time retraining runs, a folder like `models/v2/` is created, copying the active weights and saving the evaluation `metadata.json`.
- **Registry Rotation**: The platform retains the **three most recent version checkpoints**. Any older versions are moved to `models/archive/vX/` to conserve memory and disk resources.
- **Rollbacks**: If a version underperforms in production, administrators can click **Rollback to this Version** in the Admin Control Panel. The system copies the target checkpoint weights back to the active models directory and live-reloads the service, restoring previous metrics instantly.
