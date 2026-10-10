import pandas as pd
from sklearn.model_selection import train_test_split
import yaml
from pathlib import Path

def load_config():
    base_dir = Path(__file__).parent.parent
    config_path = base_dir / 'configs' / 'config.yaml'
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def load_data():
    config = load_config()
    base_dir = Path(__file__).parent.parent
    
    text_path = base_dir / config['paths']['raw_data_text']
    tabular_path = base_dir / config['paths']['raw_data_tabular']
    
    df_text = pd.read_csv(text_path)
    df_tabular = pd.read_csv(tabular_path)
    
    return df_text, df_tabular

def get_data_splits(df, target_col, config):
    test_size = config['training']['test_size']
    val_size = config['training']['val_size']
    
    # Train + Val vs Test
    train_val_df, test_df = train_test_split(
        df, 
        test_size=test_size, 
        stratify=df[target_col], 
        random_state=config['random_seed']
    )
    
    # Calculate relative val size from remaining data
    rel_val_size = val_size / (1 - test_size)
    
    train_df, val_df = train_test_split(
        train_val_df, 
        test_size=rel_val_size, 
        stratify=train_val_df[target_col], 
        random_state=config['random_seed']
    )
    
    return train_df, val_df, test_df
