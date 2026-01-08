"""
RandomForest Model Training Pipeline
=====================================
Trains a RandomForestClassifier for maternal health risk prediction.

Features:
- 80/10/10 train/validation/test split
- Feature engineering (BP_Ratio, Age_Risk, Gestational_Risk)
- StandardScaler for feature normalization
- Class balancing with 'balanced' weights
- Model and scaler serialization with joblib

Hyperparameters:
- n_estimators=200
- max_depth=15
- min_samples_split=10
- min_samples_leaf=5
- class_weight='balanced'
"""

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score
)

def engineer_features(df):
    """
    Engineer additional features from raw data.
    
    Args:
        df: DataFrame with raw features
    
    Returns:
        DataFrame with engineered features
    """
    df = df.copy()
    
    # BP Ratio (vascular resistance indicator)
    df['BP_Ratio'] = df['SystolicBP'] / df['DiastolicBP']
    
    # Age risk flag (>= 35 years)
    df['Age_Risk'] = (df['Age'] >= 35).astype(int)
    
    # Gestational risk flag (early < 12 or late > 40)
    df['Gestational_Risk'] = ((df['GestationalWeeks'] < 12) | 
                               (df['GestationalWeeks'] > 40)).astype(int)
    
    return df


def train_model(data_path, model_dir):
    """
    Train RandomForest model for maternal health risk prediction.
    
    Args:
        data_path: Path to CSV dataset
        model_dir: Directory to save trained model
    
    Returns:
        Trained model and scaler
    """
    print("="*70)
    print("MOMWATCH AI - Model Training Pipeline")
    print("="*70)
    
    # Load dataset
    print(f"\nLoading dataset from: {data_path}")
    df = pd.read_csv(data_path)
    print(f"✓ Loaded {len(df)} records")
    
    # Engineer features
    print("\nEngineering features...")
    df = engineer_features(df)
    
    # Define feature columns
    feature_cols = [
        'Age', 'SystolicBP', 'DiastolicBP', 'BloodSugar',
        'BodyTemp', 'HeartRate', 'BP_Ratio', 'GestationalWeeks'
    ]
    
    # Separate features and target
    X = df[feature_cols].values
    y = df['RiskLevel'].values
    
    print(f"✓ Feature matrix shape: {X.shape}")
    print(f"✓ Features: {feature_cols}")
    
    # Encode target labels
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)
    print(f"✓ Target classes: {label_encoder.classes_}")
    
    # Split dataset: 80% train, 10% validation, 10% test
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y_encoded, test_size=0.1, random_state=42, stratify=y_encoded
    )
    
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=0.111, random_state=42, stratify=y_train_val
    )  # 0.111 * 0.9 = 0.1 (10% of total)
    
    print(f"\n✓ Train set: {len(X_train)} samples")
    print(f"✓ Validation set: {len(X_val)} samples")
    print(f"✓ Test set: {len(X_test)} samples")
    
    # Feature scaling
    print("\nScaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)
    print("✓ Features scaled")
    
    # Train RandomForest
    print("\nTraining RandomForest model...")
    print("Hyperparameters:")
    print("  - n_estimators: 200")
    print("  - max_depth: 15")
    print("  - min_samples_split: 10")
    print("  - min_samples_leaf: 5")
    print("  - class_weight: balanced")
    
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_split=10,
        min_samples_leaf=5,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1,
        verbose=1
    )
    
    model.fit(X_train_scaled, y_train)
    print("✓ Model trained")
    
    # Evaluate on validation set
    print("\n" + "="*70)
    print("VALIDATION SET EVALUATION")
    print("="*70)
    
    y_val_pred = model.predict(X_val_scaled)
    val_accuracy = accuracy_score(y_val, y_val_pred)
    val_f1 = f1_score(y_val, y_val_pred, average='weighted')
    
    print(f"\nAccuracy: {val_accuracy:.4f}")
    print(f"F1-Score (weighted): {val_f1:.4f}")
    
    print("\nClassification Report:")
    print(classification_report(
        y_val,
        y_val_pred,
        target_names=label_encoder.classes_
    ))
    
    print("Confusion Matrix:")
    cm = confusion_matrix(y_val, y_val_pred)
    print(cm)
    
    # Feature importances
    print("\n" + "="*70)
    print("FEATURE IMPORTANCES")
    print("="*70)
    importances = sorted(
        zip(feature_cols, model.feature_importances_),
        key=lambda x: x[1],
        reverse=True
    )
    for feature, importance in importances:
        print(f"{feature:20s}: {importance:.4f}")
    
    # Save model and scaler
    print("\n" + "="*70)
    print("SAVING MODEL")
    print("="*70)
    
    model_dir = Path(model_dir)
    model_dir.mkdir(exist_ok=True)
    
    model_path = model_dir / "maternal_rf_model.joblib"
    scaler_path = model_dir / "feature_scaler.joblib"
    
    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)
    
    print(f"✓ Model saved to: {model_path}")
    print(f"✓ Scaler saved to: {scaler_path}")
    
    # Save label encoder for reference
    label_encoder_path = model_dir / "label_encoder.joblib"
    joblib.dump(label_encoder, label_encoder_path)
    print(f"✓ Label encoder saved to: {label_encoder_path}")
    
    # Save test set for evaluation script
    test_data_path = model_dir / "test_data.npz"
    np.savez(
        test_data_path,
        X_test=X_test_scaled,
        y_test=y_test
    )
    print(f"✓ Test data saved to: {test_data_path}")
    
    print("\n" + "="*70)
    print("✓ MODEL TRAINING COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print("1. Evaluate model: python evaluate.py")
    print("2. Start backend: cd ../backend && uvicorn app.main:app")
    
    return model, scaler


if __name__ == "__main__":
    # Paths
    script_dir = Path(__file__).parent
    data_path = script_dir / "data" / "maternal_health_dataset.csv"
    model_dir = script_dir / "model_store"
    
    # Check if dataset exists
    if not data_path.exists():
        print(f"ERROR: Dataset not found at {data_path}")
        print("Please run: python dataset_gen.py")
        exit(1)
    
    # Train model
    model, scaler = train_model(data_path, model_dir)
