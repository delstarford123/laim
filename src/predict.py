import joblib
import pandas as pd
import numpy as np
import os

class InseminationPredictor:
    def __init__(self, 
                 model_path='models/livestock_xgb.pkl', 
                 preprocessor_path='models/preprocessor.joblib',
                 bull_catalog_path='data/bull_catalog.csv'):
        
        # 1. Load the Trained AI Model
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"❌ Model not found at {model_path}. Run train.py first!")
        self.model = joblib.load(model_path)
        
        # 2. Load the Preprocessor (The 'rules' for formatting data)
        if not os.path.exists(preprocessor_path):
            raise FileNotFoundError(f"❌ Preprocessor not found at {preprocessor_path}.")
        self.preprocessor = joblib.load(preprocessor_path)
        
        # 3. Load the Bull Catalog (For Genetic Lookup)
        if os.path.exists(bull_catalog_path):
            self.bull_catalog = pd.read_csv(bull_catalog_path)
        else:
            print(f"⚠️ Warning: Bull catalog not found at {bull_catalog_path}. Using default values.")
            self.bull_catalog = pd.DataFrame() # Empty DF

    def enrich_data(self, cow_data):
        """
        Takes the raw cow input and adds the Bull's genetic statistics 
        (Fertility & Motility) by looking them up in the catalog.
        """
        bull_code = cow_data.get('semen_bull_code')
        
        # Default values (average) in case bull is missing or catalog is empty
        sire_fertility = 3.5
        straw_motility = 60.0
        
        # Lookup Logic
        if not self.bull_catalog.empty:
            # Find the row where bull_code matches
            bull_row = self.bull_catalog[self.bull_catalog['bull_code'] == bull_code]
            
            if not bull_row.empty:
                sire_fertility = float(bull_row.iloc[0]['sire_fertility_score'])
                straw_motility = float(bull_row.iloc[0]['straw_motility_percent'])
            else:
                print(f"ℹ️  Bull Code '{bull_code}' not found in catalog. Using averages.")
        
        # Add these new features to the cow_data dictionary
        cow_data['sire_fertility_score'] = sire_fertility
        cow_data['straw_motility_percent'] = straw_motility
            
        return cow_data

    def predict(self, cow_data):
        """
        Args:
            cow_data (dict): Dictionary containing cow metrics
        Returns:
            dict: Probability of success and boolean recommendation
        """
        # STEP 1: Enrich Data (Add Genetics)
        # This modifies cow_data to include 'sire_fertility_score' etc.
        rich_data = self.enrich_data(cow_data)
        
        # STEP 2: Convert to DataFrame
        # The pipeline expects a DataFrame, not a dict
        input_df = pd.DataFrame([rich_data])
        
        # STEP 3: Transform Data
        # Applies scaling and one-hot encoding exactly like training
        processed_data = self.preprocessor.transform(input_df)
        
        # STEP 4: AI Prediction
        # returns [probability_failure, probability_success]
        prob = self.model.predict_proba(processed_data)[0][1]
        
        # STEP 5: Decision Logic
        # 0.65 (65%) is a safe threshold for livestock investment
        recommendation = "✅ PROCEED" if prob > 0.65 else "❌ DELAY / CHECK HEALTH"
        
        return {
            "probability": round(prob * 100, 2),
            "recommendation": recommendation,
            "raw_score": float(prob),
            "bull_used": rich_data['semen_bull_code']
        }

# --- TEST BLOCK ---
# This runs only if you execute "python src/predict.py" directly
if __name__ == "__main__":
    try:
        predictor = InseminationPredictor()
        
        # Mock data representing a healthy Friesian cow
        new_cow = {
            'age_months': 36,
            'weight_kg': 450,
            'bcs_score': 3.5,
            'days_since_calving': 65,
            'milk_yield_daily': 22.5,
            'activity_index': 85,    # High activity = Good heat sign
            'breed': 'Friesian',
            'parity': 2,             # Number of previous births
            'semen_bull_code': 'BULL_A' # The code must exist in bull_catalog.csv
        }
        
        print("🔍 Analyzing Cow Data...")
        result = predictor.predict(new_cow)
        print("-" * 30)
        print(f"Result: {result['recommendation']}")
        print(f"Success Probability: {result['probability']}%")
        print("-" * 30)
        
    except Exception as e:
        print(f"❌ Error: {e}")