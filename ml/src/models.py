from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from src.features import build_text_pipeline

class TextModels:
    def __init__(self, random_state=42):
        self.cat_pipeline = Pipeline([
            ('features', build_text_pipeline()),
            ('clf', LogisticRegression(random_state=random_state, max_iter=1000, class_weight='balanced'))
        ])
        self.emo_pipeline = Pipeline([
            ('features', build_text_pipeline()),
            ('clf', LogisticRegression(random_state=random_state, max_iter=1000, class_weight='balanced'))
        ])
        
    def fit(self, X, y_cat, y_emo):
        print("Training Text Category Model...")
        self.cat_pipeline.fit(X, y_cat)
        print("Training Text Emotion Model...")
        self.emo_pipeline.fit(X, y_emo)
        return self
        
    def predict(self, X):
        cat_preds = self.cat_pipeline.predict(X)
        emo_preds = self.emo_pipeline.predict(X)
        return cat_preds, emo_preds
        
    def predict_proba(self, X):
        cat_probs = self.cat_pipeline.predict_proba(X)
        emo_probs = self.emo_pipeline.predict_proba(X)
        return cat_probs, emo_probs
