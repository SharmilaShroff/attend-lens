import joblib
import pandas as pd
import numpy as np
from pathlib import Path
import yaml

# Lazy loading variables
_text_models = None
_tab_model = None
_config = None
_models_loaded = False
_models_available = True

CRISIS_KEYWORDS = ["suicide", "self-harm", "kill myself", "end it all", "don't want to live"]

APPROACH_MAPPING = {
    "Health Issue": "Empathize with their health condition. Suggest resting and visiting a doctor. Offer flexibility with deadlines.",
    "Family or Personal Issue": "Show understanding for their personal situation. Offer a listening ear and flexible attendance options.",
    "Financial or Transport Issue": "Discuss potential financial aid or transportation alternatives. Be practical and supportive.",
    "Academic Stress or Low Interest": "Schedule an academic counseling session. Break down tasks and discuss their interests to improve engagement.",
    "Mental Health or Anxiety": "Provide a safe space. Gently encourage them to seek professional counseling or campus mental health resources.",
    "Peer or Social Issue": "Address the social dynamics carefully. Offer mediation if appropriate or a change of groups/sections.",
    "Work or Internship Commitment": "Discuss time management strategies. Help them balance work and studies, possibly offering asynchronous options.",
    "Unknown": "Reach out for a general check-in to understand their situation better."
}

def load_models_if_needed():
    global _text_models, _tab_model, _config, _models_loaded, _models_available
    
    if _models_loaded:
        return _models_available
        
    base_dir = Path(__file__).parent.parent
    config_path = base_dir / 'configs' / 'config.yaml'
    
    if not config_path.exists():
        _models_available = False
        _models_loaded = True
        return False
        
    with open(config_path, 'r') as f:
        _config = yaml.safe_load(f)
        
    text_model_path = base_dir / _config['paths']['text_model_path']
    tab_model_path = base_dir / _config['paths']['tabular_model_path']
    
    if text_model_path.exists() and tab_model_path.exists():
        try:
            # Need to import TextModels for unpickling
            from src.models import TextModels
            _text_models = joblib.load(text_model_path)
            _tab_model = joblib.load(tab_model_path)
            _models_available = True
        except Exception as e:
            print(f"Error loading models: {e}")
            _models_available = False
    else:
        _models_available = False
        
    _models_loaded = True
    return _models_available

def check_crisis(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    for kw in CRISIS_KEYWORDS:
        if kw in text_lower:
            return True
    return False

def get_top_factors(attendance_features: dict) -> list:
    # A simple heuristic to identify top factors from attendance features
    factors = []
    
    if attendance_features.get('overall_pct', 100) < 60:
        factors.append("Low overall attendance")
    if attendance_features.get('consecutive_streak', 0) >= 3:
        factors.append("High consecutive absences")
    if attendance_features.get('subjects_below_75', 0) >= 2:
        factors.append("Multiple subjects below 75%")
    if attendance_features.get('monday_ratio', 0) > 0.4:
        factors.append("Frequent Monday absences")
    if attendance_features.get('recent_trend', 0) < 0:
        factors.append("Negative recent attendance trend")
        
    # Default fallback
    if not factors:
        factors = ["No major critical factors identified"]
        
    return factors[:3]

def predict_counsel(attendance_features: dict, reason_text: str | None = None) -> dict:
    # 1. Crisis check
    if reason_text and check_crisis(reason_text):
        return {
            "is_crisis": True,
            "problem_category": "Mental Health or Anxiety",
            "emotion": "Stressed",
            "confidence": 1.0,
            "top_factors": ["CRISIS KEYWORD DETECTED"],
            "suggested_approach": "IMMEDIATE ACTION REQUIRED. Contact emergency services or crisis counseling immediately.",
            "low_confidence": False
        }
        
    # 2. Load models
    available = load_models_if_needed()
    if not available:
        return {
            "model_unavailable": True,
            "is_crisis": False
        }
        
    category = "Unknown"
    emotion = "Neutral"
    confidence = 0.0
    
    # 3. Predict
    # If text is provided and long enough, use text model for both.
    # Otherwise, use tabular model for category, default emotion.
    if reason_text and len(reason_text.strip()) > 5:
        # Predict with text
        X_text = pd.Series([reason_text])
        cat_probs, emo_probs = _text_models.predict_proba(X_text)
        
        cat_idx = np.argmax(cat_probs[0])
        emo_idx = np.argmax(emo_probs[0])
        
        category = _text_models.cat_pipeline.classes_[cat_idx]
        emotion = _text_models.emo_pipeline.classes_[emo_idx]
        
        # Combined confidence
        confidence = float((cat_probs[0][cat_idx] + emo_probs[0][emo_idx]) / 2)
    else:
        # Predict with tabular
        # Ensure all required columns exist
        cols = ['overall_pct', 'subjects_below_75', 'consecutive_streak', 
                'monday_ratio', 'friday_ratio', 'recent_trend']
        tab_data = {c: [attendance_features.get(c, 0)] for c in cols}
        X_tab = pd.DataFrame(tab_data)
        
        cat_probs = _tab_model.predict_proba(X_tab)
        cat_idx = np.argmax(cat_probs[0])
        
        category = _tab_model.classes_[cat_idx]
        emotion = "Neutral" # Cannot predict emotion from tabular easily
        confidence = float(cat_probs[0][cat_idx])
        
    # 4. Final output
    low_confidence = confidence < 0.5
    top_factors = get_top_factors(attendance_features)
    approach = APPROACH_MAPPING.get(category, APPROACH_MAPPING["Unknown"])
    
    return {
        "problem_category": category,
        "emotion": emotion,
        "confidence": round(confidence, 2),
        "top_factors": top_factors,
        "suggested_approach": approach,
        "is_crisis": False,
        "low_confidence": low_confidence
    }
