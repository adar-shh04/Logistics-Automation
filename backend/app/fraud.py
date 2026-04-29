import os
import joblib
import numpy as np
from app.config import settings

_model_cache = None

def load_model():
    global _model_cache
    if _model_cache is not None:
        return _model_cache
        
    if os.path.exists(settings.model_path):
        try:
            _model_cache = joblib.load(settings.model_path)
            return _model_cache
        except Exception as e:
            print(f"Error loading model: {e}")
            return None
    return None

def predict_risk(features: dict):
    """
    features: dict with numeric features
    returns risk_score in [0,1] (higher = more risky)
    """
    model = load_model()
    total = float(features.get('total_amount', 0) or 0)
    party_count = float(features.get('party_txn_count', 0) or 0)
    X = np.array([[total, party_count]])
    if model is None:
        # simple heuristic fallback
        score = min(1.0, total / 100000.0)
        return float(score)
    # decision_function: negative -> anomaly. We map to [0,1]
    df = model.decision_function(X)[0]
    # Normalize by typical decision range (empirical)
    # larger df => less anomalous. Convert to anomaly score in 0..1
    score = 1.0 - ( (df - (-0.5)) / (2.0) )
    score = max(0.0, min(1.0, score))
    return float(score)
