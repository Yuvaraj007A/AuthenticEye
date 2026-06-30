import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from PIL import Image

import numpy as np
import torch

# Ensure parent directory is in search path to import sibling modules
sys.path.append(str(Path(__file__).parent.parent))

from model import load_models
from preprocessing import preprocess_image_for_ensemble

# Try importing sklearn metrics
try:
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
except ImportError:
    print("[ERROR] scikit-learn is required. Run: pip install scikit-learn")
    sys.exit(1)

# Try importing matplotlib
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except ImportError:
    print("[ERROR] matplotlib is required. Run: pip install matplotlib")
    sys.exit(1)

# Try importing reportlab
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
except ImportError:
    print("[ERROR] reportlab is required. Run: pip install reportlab")
    sys.exit(1)


def generate_plots(y_true, y_scores, output_dir):
    """Generates and saves metric plots (Confusion Matrix & ROC Curve)."""
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Confusion Matrix Plot
    cm = confusion_matrix(y_true, [1 if p >= 0.5 else 0 for p in y_scores])
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.matshow(cm, cmap=plt.cm.Blues, alpha=0.3)
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(x=j, y=i, s=cm[i, j], va='center', ha='center', size='xx-large', weight='bold')
            
    ax.set_xlabel('Predictions', fontsize=12)
    ax.set_ylabel('Actuals', fontsize=12)
    ax.set_xticklabels(['', 'Real', 'Fake'])
    ax.set_yticklabels(['', 'Real', 'Fake'])
    ax.set_title('Confusion Matrix', fontsize=14, weight='bold')
    cm_path = os.path.join(output_dir, "temp_cm.png")
    plt.tight_layout()
    plt.savefig(cm_path, dpi=200)
    plt.close()
    
    # 2. ROC Curve Plot
    # Calculate ROC curve values manually or via sklearn
    from sklearn.metrics import roc_curve
    fpr, tpr, _ = roc_curve(y_true, y_scores)
    auc_val = roc_auc_score(y_true, y_scores)
    
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(fpr, tpr, color='indigo', lw=2, label=f'ROC Curve (AUC = {auc_val:.3f})')
    ax.plot([0, 1], [0, 1], color='slateblue', lw=1.5, linestyle='--')
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.set_xlabel('False Positive Rate', fontsize=11)
    ax.set_ylabel('True Positive Rate', fontsize=11)
    ax.set_title('Receiver Operating Characteristic (ROC)', fontsize=13, weight='bold')
    ax.legend(loc="lower right")
    roc_path = os.path.join(output_dir, "temp_roc.png")
    plt.tight_layout()
    plt.savefig(roc_path, dpi=200)
    plt.close()
    
    return cm_path, roc_path


def generate_pdf_report(metrics, cm_img, roc_img, pdf_path, model_meta):
    """Generates research-grade PDF report of model performance using ReportLab."""
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=25
    )
    
    heading_style = ParagraphStyle(
        'SecHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=15,
        spaceAfter=10,
        borderPadding=4
    )
    
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor('#334155'),
        spaceAfter=12,
        leading=14
    )
    
    metric_label_style = ParagraphStyle(
        'MetricLbl',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        textColor=colors.HexColor('#1e293b')
    )
    
    metric_val_style = ParagraphStyle(
        'MetricVal',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        textColor=colors.HexColor('#059669'),
        alignment=2 # Right aligned
    )

    story = []
    
    # Header
    story.append(Paragraph("AuthenticEye Forensic Detection Platform", title_style))
    story.append(Paragraph(f"RESEARCH-GRADE MODEL EVALUATION REPORT &mdash; GENERATED ON {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", subtitle_style))
    story.append(Spacer(1, 10))
    
    # Section: Executive Summary
    story.append(Paragraph("Executive Summary", heading_style))
    summary_text = (
        f"This report documents the performance metrics of the active ensemble classification model "
        f"running on the AuthenticEye deepfake verification platform. The evaluation was executed on a split "
        f"validation test suite comprising {metrics['total_samples']} samples ({metrics['real_samples']} real / "
        f"{metrics['fake_samples']} synthetic faces). The detector blends features from fine-tuned "
        f"convolutional neural networks (EfficientNet-B4 & XceptionNet) with signal-level artifacts (FFT frequency ratios & "
        f"spatial reconstruction statistics) through a fitted Logistic Regression meta-classifier."
    )
    story.append(Paragraph(summary_text, body_style))
    
    # Section: System/Model Metadata
    story.append(Paragraph("Model Configurations & Target Checkpoints", heading_style))
    meta_data = [
        [Paragraph("Active Version", metric_label_style), Paragraph(str(model_meta.get("version", "v1")), body_style)],
        [Paragraph("Checkpoint Created At", metric_label_style), Paragraph(str(model_meta.get("createdAt", "N/A")), body_style)],
        [Paragraph("Trained On Dataset", metric_label_style), Paragraph(str(model_meta.get("dataset", "N/A")), body_style)],
        [Paragraph("Hardware Device", metric_label_style), Paragraph("CUDA GPU" if torch.cuda.is_available() else "CPU Execution (Inference)", body_style)]
    ]
    t_meta = Table(meta_data, colWidths=[2.5*inch, 4.5*inch])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 15))
    
    # Section: Performance Metrics Table
    story.append(Paragraph("Key Classification Metrics", heading_style))
    metrics_data = [
        [Paragraph("Metric", metric_label_style), Paragraph("Value Score", metric_label_style)],
        [Paragraph("Accuracy", body_style), Paragraph(f"{metrics['accuracy']:.4f} ({metrics['accuracy']*100:.2f}%)", metric_val_style)],
        [Paragraph("Precision (Positive Predictive Value)", body_style), Paragraph(f"{metrics['precision']:.4f} ({metrics['precision']*100:.2f}%)", metric_val_style)],
        [Paragraph("Recall (Sensitivity / TPR)", body_style), Paragraph(f"{metrics['recall']:.4f} ({metrics['recall']*100:.2f}%)", metric_val_style)],
        [Paragraph("F1-Score (Harmonic Mean)", body_style), Paragraph(f"{metrics['f1']:.4f} ({metrics['f1']*100:.2f}%)", metric_val_style)],
        [Paragraph("Receiver Operating Characteristic (ROC AUC)", body_style), Paragraph(f"{metrics['roc_auc']:.4f}", metric_val_style)]
    ]
    
    t_metrics = Table(metrics_data, colWidths=[4.0*inch, 3.0*inch])
    t_metrics.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#f1f5f9')),
        ('LINEBELOW', (0,0), (-1,0), 1.5, colors.HexColor('#cbd5e1')),
        ('LINEBELOW', (0,1), (-1,-1), 0.5, colors.HexColor('#f1f5f9')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_metrics)
    story.append(Spacer(1, 15))
    
    # Section: Performance Visualizations
    story.append(Paragraph("Performance Visualizations", heading_style))
    
    # Embed CM and ROC side-by-side or scaled in tables
    img_width = 3.2 * inch
    img_height = 2.8 * inch
    
    rl_cm = RLImage(cm_img, width=img_width, height=img_width)
    rl_roc = RLImage(roc_img, width=img_width, height=2.6*inch)
    
    vis_data = [[rl_cm, rl_roc]]
    t_vis = Table(vis_data, colWidths=[3.5*inch, 3.5*inch])
    t_vis.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(KeepTogether([t_vis]))
    
    doc.build(story)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=str, default=None, help="Path to val split data directory")
    parser.add_argument("--output-dir", type=str, default=None, help="Directory to save metric outcomes")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of validation images to test per class")
    args = parser.parse_args()

    # Determine default paths
    script_dir = Path(__file__).parent
    ai_service_dir = script_dir.parent
    
    data_dir = args.data_dir
    if not data_dir:
        data_dir = os.path.join(ai_service_dir, "training", "prepared_data", "val")
        
    output_dir = args.output_dir
    if not output_dir:
        output_dir = os.path.join(ai_service_dir, "metrics_eval")
        
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"[EVAL] Targeting validation split folder: {data_dir}")
    print(f"[EVAL] Outputs will be stored in: {output_dir}")
    
    # Load model metadata if current.json exists
    current_json_path = os.path.join(ai_service_dir, "models", "current.json")
    model_meta = {}
    if os.path.exists(current_json_path):
        try:
            with open(current_json_path, "r") as f:
                model_meta = json.load(f)
        except Exception as e:
            print(f"[WARNING] Failed to parse models/current.json: {e}")
            
    # Load active models
    print("[EVAL] Initializing and loading EnsembleDetector...")
    detector = load_models()
    
    real_path = Path(data_dir) / "real"
    fake_path = Path(data_dir) / "fake"
    
    real_images = list(real_path.glob("*.jpg")) + list(real_path.glob("*.png")) + list(real_path.glob("*.jpeg"))
    fake_images = list(fake_path.glob("*.jpg")) + list(fake_path.glob("*.png")) + list(fake_path.glob("*.jpeg"))
    
    if args.limit is not None:
        print(f"[EVAL] Slicing dataset from {len(real_images)} real / {len(fake_images)} fake to max {args.limit} per class.")
        real_images = real_images[:args.limit]
        fake_images = fake_images[:args.limit]
        
    print(f"[EVAL] Evaluating on {len(real_images)} real images and {len(fake_images)} fake images.")
    
    y_true = []
    y_scores = []
    
    # Process Real Images
    for idx, img_p in enumerate(real_images):
        try:
            pil_img = Image.open(img_p).convert("RGB")
            tensor, found = preprocess_image_for_ensemble(pil_img)
            res = detector.predict(tensor, pil_img)
            y_true.append(0)
            y_scores.append(res["deepfake_probability"])
        except Exception as e:
            print(f"[EVAL] Failed to process real image {img_p.name}: {e}")
            
    # Process Fake Images
    for idx, img_p in enumerate(fake_images):
        try:
            pil_img = Image.open(img_p).convert("RGB")
            tensor, found = preprocess_image_for_ensemble(pil_img)
            res = detector.predict(tensor, pil_img)
            y_true.append(1)
            y_scores.append(res["deepfake_probability"])
        except Exception as e:
            print(f"[EVAL] Failed to process fake image {img_p.name}: {e}")
            
    if len(y_true) == 0:
        print("[ERROR] No validation samples were successfully evaluated.")
        sys.exit(1)
        
    y_true = np.array(y_true)
    y_scores = np.array(y_scores)
    y_pred = np.array([1 if s >= 0.5 else 0 for s in y_scores])
    
    # Calculate metrics
    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    
    try:
        auc = roc_auc_score(y_true, y_scores)
    except Exception:
        auc = 0.5
        
    cm = confusion_matrix(y_true, y_pred)
    
    metrics = {
        "accuracy": round(float(acc), 4),
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1": round(float(f1), 4),
        "roc_auc": round(float(auc), 4),
        "confusion_matrix": cm.tolist(),
        "total_samples": len(y_true),
        "real_samples": len(real_images),
        "fake_samples": len(fake_images)
    }
    
    # Write metrics to JSON file
    metrics_json_path = os.path.join(output_dir, "metrics.json")
    with open(metrics_json_path, "w") as f:
        json.dump(metrics, f, indent=4)
    print(f"[EVAL] Metrics saved to {metrics_json_path}")
    
    # Generate metric charts
    print("[EVAL] Plotting CM and ROC charts...")
    cm_img, roc_img = generate_plots(y_true, y_scores, output_dir)
    
    # Generate PDF Forensic report
    pdf_report_path = os.path.join(output_dir, "evaluation_report.pdf")
    print(f"[EVAL] Rendering forensic ReportLab PDF to {pdf_report_path}...")
    generate_pdf_report(metrics, cm_img, roc_img, pdf_report_path, model_meta)
    
    # Cleanup temp images
    try:
        os.unlink(cm_img)
        os.unlink(roc_img)
    except Exception:
        pass
        
    print("[SUCCESS] Evaluation metrics compilation and PDF rendering finished!")


if __name__ == "__main__":
    main()
