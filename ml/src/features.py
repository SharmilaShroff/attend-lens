import pandas as pd
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer

class TextFeatureExtractor(BaseEstimator, TransformerMixin):
    def __init__(self):
        self.keywords = ['sick', 'fever', 'family', 'money', 'bus', 'stress', 'exam', 'job']
        
    def fit(self, X, y=None):
        return self
        
    def transform(self, X, y=None):
        if isinstance(X, pd.Series):
            X_series = X
        elif isinstance(X, pd.DataFrame) and X.shape[1] == 1:
            X_series = X.iloc[:, 0]
        else:
            X_series = pd.Series(X)
        
        # Extracted features
        features = pd.DataFrame(index=X_series.index)
        
        for kw in self.keywords:
            features[f'has_{kw}'] = X_series.astype(str).str.lower().str.contains(kw, na=False).astype(float)
            
        return features.values

def build_text_pipeline():
    # Use ColumnTransformer to apply TF-IDF to text and keep extracted features
    # Wait, we need to pass a series to TF-IDF. 
    # Better to have two pipelines and combine them using FeatureUnion.
    from sklearn.pipeline import FeatureUnion
    
    class ItemSelector(BaseEstimator, TransformerMixin):
        def fit(self, x, y=None):
            return self
        def transform(self, data_dict):
            return data_dict
            
    text_features = FeatureUnion([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=1000)),
        ('custom_features', TextFeatureExtractor())
    ])
    
    return text_features

def build_tabular_transformer():
    # Since these are already numeric, we can just pass them through or scale them.
    from sklearn.preprocessing import StandardScaler
    
    numeric_features = [
        'overall_pct', 'subjects_below_75', 'consecutive_streak', 
        'monday_ratio', 'friday_ratio', 'recent_trend'
    ]
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), numeric_features)
        ],
        remainder='drop'
    )
    return preprocessor
