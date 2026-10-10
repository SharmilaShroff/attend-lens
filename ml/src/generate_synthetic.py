import random
import string
import pandas as pd
import numpy as np
import os
import yaml
from pathlib import Path

def load_config():
    base_dir = Path(__file__).parent.parent
    config_path = base_dir / 'configs' / 'config.yaml'
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def generate_text_data(config, num_samples=2000):
    random.seed(config['random_seed'])
    
    categories = config['categories']['problem_categories']
    emotions = config['categories']['emotions']
    
    templates = {
        "Health Issue": [
            "I have been feeling {symptom} for the past {duration}.",
            "Diagnosed with {illness}, need {duration} to recover.",
            "I was sick with {illness} and couldn't attend.",
            "Suffering from {symptom}, doctor advised rest."
        ],
        "Family or Personal Issue": [
            "Had to attend a family {event}.",
            "Family emergency came up suddenly.",
            "Personal issues at home, taking {duration} off.",
            "My {relative} is unwell, need to take care of them."
        ],
        "Financial or Transport Issue": [
            "My {transport} broke down.",
            "Couldn't afford the bus fare this week.",
            "Stuck in traffic for hours due to {event}.",
            "Having some money issues, need to work extra shifts."
        ],
        "Academic Stress or Low Interest": [
            "Feeling overwhelmed with the {subject} assignments.",
            "Don't find the classes interesting anymore.",
            "Struggling to keep up with the coursework.",
            "I have too many exams this week."
        ],
        "Mental Health or Anxiety": [
            "Feeling very anxious about my performance.",
            "Having a panic attack, couldn't make it.",
            "Mental health hasn't been great lately.",
            "Depressed and unable to leave the house."
        ],
        "Peer or Social Issue": [
            "Having trouble with some classmates.",
            "Feeling isolated and bullied.",
            "Got into a fight with a friend.",
            "Social anxiety is making it hard to attend."
        ],
        "Work or Internship Commitment": [
            "Clash with my internship schedule.",
            "Had to work a double shift at my job.",
            "Called into work unexpectedly.",
            "Job interview today, couldn't attend."
        ],
        "Unknown": [
            "I won't be there.",
            "Absent today.",
            "Can't make it to class.",
            "Not coming."
        ]
    }
    
    fillers = {
        "symptom": ["fever", "headache", "stomach pain", "severe cold"],
        "illness": ["covid", "flu", "dengue", "food poisoning"],
        "duration": ["few days", "a week", "2 days", "some time"],
        "event": ["wedding", "funeral", "gathering", "accident"],
        "relative": ["mother", "father", "sister", "brother"],
        "transport": ["car", "bike", "bus", "train"],
        "subject": ["math", "science", "programming", "history"]
    }
    
    data = []
    for _ in range(num_samples):
        cat = random.choice(categories)
        emo = random.choice(emotions)
        
        template = random.choice(templates[cat])
        kwargs = {}
        for k, v in fillers.items():
            if f"{{{k}}}" in template:
                kwargs[k] = random.choice(v)
        
        text = template.format(**kwargs)
        
        # Randomly inject minor typos or varied lengths
        if random.random() < 0.1:
            text = text.lower()
        if random.random() < 0.05:
            text = text + " Sorry."
            
        data.append({"text": text, "problem_category": cat, "emotion": emo})
        
    df = pd.DataFrame(data)
    
    # Ensure all classes have some representation
    return df

def generate_tabular_data(config, num_samples=1000):
    np.random.seed(config['random_seed'])
    random.seed(config['random_seed'])
    
    categories = config['categories']['problem_categories']
    
    data = []
    for _ in range(num_samples):
        cat = random.choice(categories)
        
        # Generate features that somewhat correlate with category
        if cat == "Health Issue":
            overall_pct = np.random.uniform(50, 95)
            consecutive_streak = np.random.randint(2, 7)
            monday_ratio = np.random.uniform(0.1, 0.3)
        elif cat == "Academic Stress or Low Interest":
            overall_pct = np.random.uniform(30, 70)
            consecutive_streak = np.random.randint(1, 4)
            monday_ratio = np.random.uniform(0.2, 0.6)
        elif cat == "Work or Internship Commitment":
            overall_pct = np.random.uniform(60, 85)
            consecutive_streak = np.random.randint(1, 3)
            monday_ratio = np.random.uniform(0.3, 0.8) # Often absent on Mondays
        else:
            overall_pct = np.random.uniform(40, 90)
            consecutive_streak = np.random.randint(1, 5)
            monday_ratio = np.random.uniform(0.1, 0.5)
            
        friday_ratio = np.random.uniform(0.1, 0.5)
        subjects_below_75 = np.random.randint(0, 5)
        recent_trend = np.random.choice([-1, 0, 1], p=[0.3, 0.5, 0.2])
        
        data.append({
            "overall_pct": overall_pct,
            "subjects_below_75": subjects_below_75,
            "consecutive_streak": consecutive_streak,
            "monday_ratio": monday_ratio,
            "friday_ratio": friday_ratio,
            "recent_trend": recent_trend,
            "problem_category": cat
        })
        
    df = pd.DataFrame(data)
    return df

if __name__ == "__main__":
    config = load_config()
    
    base_dir = Path(__file__).parent.parent
    text_path = base_dir / config['paths']['raw_data_text']
    tabular_path = base_dir / config['paths']['raw_data_tabular']
    
    text_path.parent.mkdir(parents=True, exist_ok=True)
    
    df_text = generate_text_data(config)
    df_tabular = generate_tabular_data(config)
    
    df_text.to_csv(text_path, index=False)
    df_tabular.to_csv(tabular_path, index=False)
    print(f"Generated {len(df_text)} text samples and {len(df_tabular)} tabular samples.")
