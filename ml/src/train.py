import pandas as pd
import numpy as np
import yaml
import joblib
from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import StratifiedKFold, GridSearchCV

from src.data import load_data, get_data_splits, load_config
from src.features import build_text_pipeline, build_tabular_transformer
from src.models import TextModels

def train_models():
    config = load_config()
    df_text, df_tabular = load_data()
    
    # Train text models
    train_text, val_text, test_text = get_data_splits(df_text, 'problem_category', config)
    
    text_models = TextModels(random_state=config['random_seed'])
    text_models.fit(
        train_text['text'], 
        train_text['problem_category'], 
        train_text['emotion']
    )
    
    cat_preds, emo_preds = text_models.predict(test_text['text'])
    print("Text Model - Category Classification Report:")
    print(classification_report(test_text['problem_category'], cat_preds))
    print("Text Model - Emotion Classification Report:")
    print(classification_report(test_text['emotion'], emo_preds))
    
    # Train tabular model
    train_tab, val_tab, test_tab = get_data_splits(df_tabular, 'problem_category', config)
    
    feature_cols = ['overall_pct', 'subjects_below_75', 'consecutive_streak', 
                    'monday_ratio', 'friday_ratio', 'recent_trend']
    
    tab_pipeline = Pipeline([
        ('features', build_tabular_transformer()),
        ('clf', RandomForestClassifier(random_state=config['random_seed'], class_weight='balanced'))
    ])
    
    # Optional: Grid search for RandomForest
    param_grid = {
        'clf__n_estimators': [50, 100],
        'clf__max_depth': [5, 10, None]
    }
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=config['random_seed'])
    grid_search = GridSearchCV(tab_pipeline, param_grid, cv=cv, scoring='f1_macro')
    
    print("Training Tabular Model...")
    grid_search.fit(train_tab[feature_cols], train_tab['problem_category'])
    best_tab_model = grid_search.best_estimator_
    
    tab_preds = best_tab_model.predict(test_tab[feature_cols])
    print("Tabular Model Classification Report:")
    print(classification_report(test_tab['problem_category'], tab_preds))
    
    # Save models
    base_dir = Path(__file__).parent.parent
    models_dir = base_dir / config['paths']['model_dir']
    models_dir.mkdir(parents=True, exist_ok=True)
    
    joblib.dump(text_models, base_dir / config['paths']['text_model_path'])
    joblib.dump(best_tab_model, base_dir / config['paths']['tabular_model_path'])
    print("Models saved.")

if __name__ == "__main__":
    train_models()
