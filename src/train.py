import xgboost as xgb
import joblib
import numpy as np
import pandas as pd
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from imblearn.over_sampling import SMOTE
from preprocess import LivestockPreprocessor

def load_and_merge_data(farm_path, bull_path):
    """
    Combines Farm Records with Genetic Bull Data.
    Returns a merged DataFrame.
    """
    print(f"🔄 Loading data from {farm_path} and {bull_path}...")
    
    # 1. Load the main farm data
    df_main = pd.read_csv(farm_path)
    
    # 2. Load the Bull Catalog
    if not os.path.exists(bull_path):
        raise FileNotFoundError(f"❌ Bull catalog not found at {bull_path}")
        
    df_bulls = pd.read_csv(bull_path)
    
    # 3. Merge them on 'semen_bull_code' -> 'bull_code'
    # This adds the bull's fertility score and motility to the cow's record
    df_merged = pd.merge(
        df_main, 
        df_bulls[['bull_code', 'sire_fertility_score', 'straw_motility_percent']], 
        left_on='semen_bull_code', 
        right_on='bull_code', 
        how='left'
    )
    
    # Drop the extra key column if it exists
    if 'bull_code' in df_merged.columns:
        df_merged.drop(columns=['bull_code'], inplace=True)
    
    print("✅ Data Merged: Added Genetic Info to Cow Records")
    return df_merged

def train_model(farm_path, bull_path, model_save_path='models/livestock_xgb.pkl'):
    print("🚀 Starting Training Pipeline...")
    
    # --- STEP 1: PREPARE DATA ---
    # Merge the files first
    merged_df = load_and_merge_data(farm_path, bull_path)
    
    # Save to a temporary file so the Preprocessor can read it
    temp_data_path = 'data/temp_merged_training.csv'
    merged_df.to_csv(temp_data_path, index=False)
    
    # --- STEP 2: PREPROCESS ---
    processor = LivestockPreprocessor()
    # pass the merged temporary file to the processor
    X, y = processor.fit_transform_save(temp_data_path)
    
    # --- STEP 3: SPLIT DATA ---
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # --- STEP 4: HANDLE IMBALANCE (SMOTE) ---
    # Generates synthetic examples of the minority class (usually 'Success')
    print("⚖️  Balancing dataset with SMOTE...")
    smote = SMOTE(random_state=42)
    X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)
    
    # --- STEP 5: INITIALIZE XGBOOST ---
    model = xgb.XGBClassifier(
        objective='binary:logistic',
        n_estimators=200,
        learning_rate=0.05,
        max_depth=5,
        eval_metric='logloss'
        # use_label_encoder=False is deprecated in newer XGBoost versions, usually safe to omit or keep
    )
    
    # --- STEP 6: TRAIN ---
    print("🧠 Training XGBoost Model...")
    model.fit(X_train_resampled, y_train_resampled)
    
    # --- STEP 7: EVALUATE ---
    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    print(f"📊 Model Accuracy: {accuracy * 100:.2f}%")
    print("Classification Report:\n", classification_report(y_test, predictions))
    
    # --- STEP 8: SAVE MODEL ---
    # Ensure the models directory exists
    os.makedirs(os.path.dirname(model_save_path), exist_ok=True)
    joblib.dump(model, model_save_path)
    print(f"💾 Model saved to {model_save_path}")
    
    # Optional: Clean up temp file
    # os.remove(temp_data_path) 

if __name__ == "__main__":
    # Define paths
    farm_csv = 'data/farm_data.csv'
    bull_csv = 'data/bull_catalog.csv'
    
    # Check if files exist
    if not os.path.exists(farm_csv):
        print(f"⚠️  Missing {farm_csv}. Please create it in the data/ folder.")
    elif not os.path.exists(bull_csv):
        print(f"⚠️  Missing {bull_csv}. Please create it in the data/ folder.")
    else:
        # Run the full pipeline
        train_model(farm_csv, bull_csv)