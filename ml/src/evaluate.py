import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
from pathlib import Path
from sklearn.metrics import classification_report, confusion_matrix, f1_score

from src.data import load_data, get_data_splits, load_config
from src.models import TextModels

def plot_confusion_matrix(y_true, y_pred, labels, title, save_path):
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=labels, yticklabels=labels)
    plt.title(title)
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()

def evaluate():
    config = load_config()
    df_text, df_tabular = load_data()
    
    base_dir = Path(__file__).parent.parent
    reports_dir = base_dir / config['paths']['reports_dir']
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    text_model_path = base_dir / config['paths']['text_model_path']
    tabular_model_path = base_dir / config['paths']['tabular_model_path']
    
    if not text_model_path.exists() or not tabular_model_path.exists():
        print("Models not found. Train them first.")
        return
        
    text_models = joblib.load(text_model_path)
    tab_model = joblib.load(tabular_model_path)
    
    _, _, test_text = get_data_splits(df_text, 'problem_category', config)
    _, _, test_tab = get_data_splits(df_tabular, 'problem_category', config)
    
    # Evaluate text model
    cat_preds, emo_preds = text_models.predict(test_text['text'])
    
    print("--- Text Model: Category ---")
    print(classification_report(test_text['problem_category'], cat_preds))
    plot_confusion_matrix(
        test_text['problem_category'], cat_preds, 
        config['categories']['problem_categories'],
        "Text Model: Problem Category",
        reports_dir / "text_category_cm.png"
    )
    
    print("--- Text Model: Emotion ---")
    print(classification_report(test_text['emotion'], emo_preds))
    plot_confusion_matrix(
        test_text['emotion'], emo_preds, 
        config['categories']['emotions'],
        "Text Model: Emotion",
        reports_dir / "text_emotion_cm.png"
    )
    
    # Evaluate tabular model
    feature_cols = ['overall_pct', 'subjects_below_75', 'consecutive_streak', 
                    'monday_ratio', 'friday_ratio', 'recent_trend']
    tab_preds = tab_model.predict(test_tab[feature_cols])
    print("--- Tabular Model: Category ---")
    print(classification_report(test_tab['problem_category'], tab_preds))
    plot_confusion_matrix(
        test_tab['problem_category'], tab_preds, 
        config['categories']['problem_categories'],
        "Tabular Model: Problem Category",
        reports_dir / "tabular_category_cm.png"
    )

if __name__ == "__main__":
    evaluate()
