"""
Layer 2: Machine Learning Model - RandomForest Predictor
=========================================================
Loads pre-trained RandomForestClassifier and provides risk predictions
with explainability (feature importances for XAI).

Feature Engineering:
- BP_Ratio = Systolic / Diastolic (vascular resistance indicator)
- Age_Risk_Score = 1 if age>=35 else 0
- Gestational_Risk = 1 if weeks>40 or weeks<12 else 0

Error Handling:
- All operations wrapped in try-except
- Raises MLModelException to trigger circuit breaker
- Logs full traceback for debugging
"""

import joblib
import numpy as np
from typing import Dict, Any, Optional
from pathlib import Path
from app.engine.sanity import ClinicalVitals
from app.engine.rules import RiskLevel
from app.config import settings
from app.utils.logger import logger


class MLModelException(Exception):
    """Custom exception for ML model failures."""
    pass


class MaternalHealthPredictor:
    """
    RandomForest-based maternal health risk predictor with XAI support.
    """
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.label_encoder = None
        self.feature_names = [
            "age", "systolic_bp", "diastolic_bp", "blood_sugar",
            "body_temp", "heart_rate", "BP_Ratio", "gestational_weeks"
        ]
        self.model_version = "RandomForest_v1.2.0"
        self._is_loaded = False
    
    def load_model(self) -> None:
        """
        Load pre-trained model and scaler from disk.
        
        Raises:
            MLModelException: If model files not found or corrupt
        """
        try:
            model_path = Path(settings.MODEL_PATH)
            scaler_path = Path(settings.SCALER_PATH)
            encoder_path = Path(settings.LABEL_ENCODER_PATH)
            
            if not model_path.exists():
                raise MLModelException(
                    f"Model file not found: {settings.MODEL_PATH}. "
                    "Please train the model first using ml_ops/train.py"
                )
            
            if not scaler_path.exists():
                raise MLModelException(
                    f"Scaler file not found: {settings.SCALER_PATH}. "
                    "Please train the model first using ml_ops/train.py"
                )
            
            if not encoder_path.exists():
                raise MLModelException(
                    f"Label encoder not found: {settings.LABEL_ENCODER_PATH}. "
                    "Please train the model first using ml_ops/train.py"
                )
            
            logger.info(f"Loading ML model from {settings.MODEL_PATH}")
            self.model = joblib.load(settings.MODEL_PATH)
            
            logger.info(f"Loading feature scaler from {settings.SCALER_PATH}")
            self.scaler = joblib.load(settings.SCALER_PATH)
            
            logger.info(f"Loading label encoder from {settings.LABEL_ENCODER_PATH}")
            self.label_encoder = joblib.load(settings.LABEL_ENCODER_PATH)
            
            self._is_loaded = True
            logger.info(f"✓ ML model loaded successfully: {self.model_version}")
        
        except Exception as e:
            logger.error(f"Failed to load ML model: {str(e)}", exc_info=True)
            raise MLModelException(f"Model loading failed: {str(e)}") from e
    
    def _engineer_features(self, vitals: ClinicalVitals) -> np.ndarray:
        """
        Engineer features from clinical vitals.
        
        Args:
            vitals: Validated clinical vitals
        
        Returns:
            Numpy array of engineered features
        """
        # Calculate derived features
        bp_ratio = vitals.systolic_bp / vitals.diastolic_bp if vitals.diastolic_bp > 0 else 0
        
        # Create feature vector (8 features)
        features = np.array([
            vitals.age,
            vitals.systolic_bp,
            vitals.diastolic_bp,
            vitals.blood_sugar,
            vitals.body_temp,
            vitals.heart_rate,
            bp_ratio,
            vitals.gestational_weeks
        ]).reshape(1, -1)
        
        return features
    
    def predict(self, vitals: ClinicalVitals) -> Dict[str, Any]:
        """
        Predict maternal health risk using ML model.
        
        Args:
            vitals: Validated clinical vitals
        
        Returns:
            Dictionary containing:
            - risk_level: Predicted RiskLevel
            - confidence: Prediction confidence (0-1)
            - feature_importances: Dict of feature importances for XAI
            - model_version: Model version string
            - engine_source: "ML_MODEL"
        
        Raises:
            MLModelException: If prediction fails
        """
        if not self._is_loaded:
            raise MLModelException("Model not loaded. Call load_model() first.")
        
        try:
            # Engineer features
            features = self._engineer_features(vitals)
            
            # Scale features
            features_scaled = self.scaler.transform(features)
            
            # Get prediction probabilities
            probabilities = self.model.predict_proba(features_scaled)[0]
            
            # Get class prediction
            prediction = self.model.predict(features_scaled)[0]
            
            # Map prediction to RiskLevel using label encoder
            risk_label = self.label_encoder.inverse_transform([prediction])[0]
            risk_level = RiskLevel(risk_label)
            
            # Get confidence (max probability)
            confidence = float(np.max(probabilities))
            
            # Extract feature importances for XAI
            feature_importances = dict(zip(
                self.feature_names,
                [float(x) for x in self.model.feature_importances_]
            ))
            
            # Sort by importance descending
            feature_importances = dict(
                sorted(feature_importances.items(), key=lambda x: x[1], reverse=True)
            )
            
            logger.info(
                f"ML prediction: {risk_level.value} (confidence: {confidence:.2f})",
                extra={
                    "risk_level": risk_level.value,
                    "confidence": confidence,
                    "model_version": self.model_version
                }
            )
            
            return {
                "risk_level": risk_level,
                "confidence": confidence,
                "feature_importances": feature_importances,
                "model_version": self.model_version,
                "engine_source": "ML_MODEL",
                "probabilities": {
                    "LOW": float(probabilities[0]) if len(probabilities) > 0 else 0.0,
                    "MEDIUM": float(probabilities[1]) if len(probabilities) > 1 else 0.0,
                    "HIGH": float(probabilities[2]) if len(probabilities) > 2 else 0.0,
                    "CRITICAL": float(probabilities[3]) if len(probabilities) > 3 else 0.0
                }
            }
        
        except Exception as e:
            logger.error(f"ML model prediction failed: {str(e)}", exc_info=True)
            raise MLModelException(f"Prediction failed: {str(e)}") from e
    
    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._is_loaded


# Global predictor instance
predictor = MaternalHealthPredictor()
