"""
Model Evaluation Script
=======================
Evaluates trained RandomForest model on test set.

Metrics:
- Accuracy, Precision, Recall, F1-score
- Per-class metrics
- Confusion matrix
- Feature importances visualization
"""

import numpy as np
import pandas as pd
import joblib
import json
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
    roc_curve
)
from sklearn.preprocessing import label_binarize


def evaluate_model(model_dir):
    """
    Evaluate trained model on test set.
    
    Args:
        model_dir: Directory containing trained model and test data
    """
    print("="*70)
    print("MOMWATCH AI - Model Evaluation")
    print("="*70)
    
    model_dir = Path(model_dir)
    
    # Load model and test data
    print("\nLoading model and test data...")
    model = joblib.load(model_dir / "maternal_rf_model.joblib")
    scaler = joblib.load(model_dir / "feature_scaler.joblib")
    label_encoder = joblib.load(model_dir / "label_encoder.joblib")
    
    test_data = np.load(model_dir / "test_data.npz")
    X_test = test_data['X_test']
    y_test = test_data['y_test']
    
    print(f"✓ Model loaded")
    print(f"✓ Test set: {len(X_test)} samples")
    
    # Make predictions
    print("\nGenerating predictions...")
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)
    
    # Calculate metrics
    print("\n" + "="*70)
    print("PERFORMANCE METRICS")
    print("="*70)
    
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average='weighted')
    recall = recall_score(y_test, y_pred, average='weighted')
    f1 = f1_score(y_test, y_pred, average='weighted')
    
    print(f"\nOverall Metrics:")
    print(f"  Accuracy:  {accuracy:.4f}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1-Score:  {f1:.4f}")
    
    # Per-class metrics
    print("\n" + "-"*70)
    print("Per-Class Classification Report:")
    print("-"*70)
    print(classification_report(
        y_test,
        y_pred,
        target_names=label_encoder.classes_,
        digits=4
    ))
    
    # Confusion Matrix
    print("\n" + "-"*70)
    print("Confusion Matrix:")
    print("-"*70)
    cm = confusion_matrix(y_test, y_pred)
    print(cm)
    
    # Plot confusion matrix
    plt.figure(figsize=(10, 8))
    sns.heatmap(
        cm,
        annot=True,
        fmt='d',
        cmap='Blues',
        xticklabels=label_encoder.classes_,
        yticklabels=label_encoder.classes_
    )
    plt.title('Confusion Matrix - Maternal Health Risk Prediction')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.tight_layout()
    plt.savefig(model_dir / 'confusion_matrix.png', dpi=300)
    print(f"✓ Confusion matrix saved to: {model_dir / 'confusion_matrix.png'}")
    
    # Feature Importances
    print("\n" + "-"*70)
    print("Feature Importances:")
    print("-"*70)
    feature_names = [
        'Age', 'SystolicBP', 'DiastolicBP', 'BloodSugar',
        'BodyTemp', 'HeartRate', 'BP_Ratio', 'GestationalWeeks'
    ]
    importances = sorted(
        zip(feature_names, model.feature_importances_),
        key=lambda x: x[1],
        reverse=True
    )
    for feature, importance in importances:
        print(f"  {feature:20s}: {importance:.4f}")
    
    # Plot feature importances
    plt.figure(figsize=(10, 6))
    features, values = zip(*importances)
    plt.barh(features, values)
    plt.xlabel('Importance')
    plt.title('Feature Importances - RandomForest Model')
    plt.tight_layout()
    plt.savefig(model_dir / 'feature_importances.png', dpi=300)
    print(f"✓ Feature importances plot saved to: {model_dir / 'feature_importances.png'}")
    
    # ROC-AUC (multi-class)
    print("\n" + "-"*70)
    print("ROC-AUC Scores (One-vs-Rest):")
    print("-"*70)
    
    y_test_bin = label_binarize(y_test, classes=range(len(label_encoder.classes_)))
    
    roc_auc_scores = {}
    for i, class_name in enumerate(label_encoder.classes_):
        try:
            roc_auc = roc_auc_score(y_test_bin[:, i], y_pred_proba[:, i])
            roc_auc_scores[class_name] = roc_auc
            print(f"  {class_name:15s}: {roc_auc:.4f}")
        except:
            print(f"  {class_name:15s}: N/A")
    
    # Save metrics to JSON
    metrics = {
        "overall": {
            "accuracy": float(accuracy),
            "precision": float(precision),
            "recall": float(recall),
            "f1_score": float(f1)
        },
        "per_class": {
            class_name: {
                "precision": float(precision_score(y_test == i, y_pred == i)),
                "recall": float(recall_score(y_test == i, y_pred == i)),
                "f1_score": float(f1_score(y_test == i, y_pred == i))
            }
            for i, class_name in enumerate(label_encoder.classes_)
        },
        "roc_auc": roc_auc_scores,
        "confusion_matrix": cm.tolist(),
        "feature_importances": dict(importances)
    }
    
    metrics_path = model_dir / "evaluation_metrics.json"
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print(f"\n✓ Metrics saved to: {metrics_path}")
    
    print("\n" + "="*70)
    print("✓ EVALUATION COMPLETE")
    print("="*70)


if __name__ == "__main__":
    model_dir = Path(__file__).parent / "model_store"
    
    if not (model_dir / "maternal_rf_model.joblib").exists():
        print("ERROR: Trained model not found!")
        print("Please run: python train.py")
        exit(1)
    
    evaluate_model(model_dir)
