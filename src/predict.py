import joblib
import pandas as pd
import numpy as np
import os

class InseminationPredictor:
    def __init__(self, 
                 model_path='models/livestock_xgb.pkl', 
                 preprocessor_path='models/preprocessor.joblib',
                 bull_catalog_path='data/bull_catalog.csv',
                 weather_csv_path='data/weather_data.csv'):
        
        # 1. Load Resources
        self._load_resource(model_path, 'model')
        self._load_resource(preprocessor_path, 'preprocessor')
        
        # 2. Load Data Tables
        self.bull_catalog = self._load_csv(bull_catalog_path, "Bull Catalog")
        self.weather_csv = weather_csv_path

    def _load_resource(self, path, name):
        """Helper to safely load joblib files."""
        if os.path.exists(path):
            setattr(self, name, joblib.load(path))
        else:
            raise FileNotFoundError(f"❌ {name.capitalize()} not found at {path}. Run train.py first.")

    def _load_csv(self, path, name):
        """Helper to safely load CSV files."""
        if os.path.exists(path):
            return pd.read_csv(path)
        print(f"⚠️ Warning: {name} not found at {path}. Using default values.")
        return pd.DataFrame()

    def get_genetic_data(self, bull_code):
        """Fetches fertility and motility scores for a specific bull."""
        defaults = {'sire_fertility_score': 3.5, 'straw_motility_percent': 60.0}
        
        if self.bull_catalog.empty:
            return defaults
            
        bull_row = self.bull_catalog[self.bull_catalog['bull_code'] == bull_code]
        
        if not bull_row.empty:
            return {
                'sire_fertility_score': float(bull_row.iloc[0]['sire_fertility_score']),
                'straw_motility_percent': float(bull_row.iloc[0]['straw_motility_percent'])
            }
        return defaults

    def get_weather_data(self, location="Kakamega"):
        """Fetches the latest weather conditions (THI)."""
        defaults = {'avg_temp_c': 22.0, 'humidity_percent': 60.0, 'thi_index': 68.0}

        try:
            if not os.path.exists(self.weather_csv):
                return defaults
            
            df = pd.read_csv(self.weather_csv)
            if df.empty:
                return defaults
                
            loc_data = df[df['location'] == location]
            latest = loc_data.iloc[-1] if not loc_data.empty else df.iloc[-1]

            return {
                'avg_temp_c': float(latest['avg_temp_c']),
                'humidity_percent': float(latest['humidity_percent']),
                'thi_index': float(latest['thi_index'])
            }
        except Exception as e:
            print(f"⚠️ Weather Read Error: {e}")
            return defaults

    def predict(self, raw_input):
        """Main pipeline: Enriches Data -> Transforms -> Predicts."""
        try:
            # --- STEP 1: PREPARE DATA ---
            data = raw_input.copy()
            
            # A. Inject Genetics
            genetics = self.get_genetic_data(data.get('semen_bull_code'))
            data.update(genetics)
            
            # B. Inject Weather
            weather = self.get_weather_data(location="Kakamega")
            data.update(weather)
            
            # Convert to DataFrame
            input_df = pd.DataFrame([data])
            
            print(f"🔍 AI Context | THI: {weather['thi_index']} | Bull Fertility: {genetics['sire_fertility_score']}")

            # --- STEP 2: TRANSFORM ---
            try:
                processed_data = self.preprocessor.transform(input_df)
            except KeyError as e:
                return {'error': f"Data Mismatch. Model expected columns: {str(e)}"}

            # --- STEP 3: PREDICT ---
            prob = self.model.predict_proba(processed_data)[:, 1][0]
            
            # --- STEP 4: RESULT (CRITICAL FIX IS HERE) ---
            return {
                'probability': round(prob * 100, 1),
                'raw_score': prob,
                'recommendation': "✅ PROCEED" if prob > 0.65 else "❌ DELAY / CHECK HEALTH",
                'thi_context': weather['thi_index'],
                'explanation': self._explain(prob, weather['thi_index']),
                
                # THIS LINE IS WHAT WAS MISSING:
                'bull_used': data.get('semen_bull_code', 'Unknown') 
            }

        except Exception as e:
            return {'error': f"Prediction Failed: {str(e)}"}

    def _explain(self, prob, thi):
        """Generates a human-readable reason."""
        if prob > 0.75:
            return "Excellent conditions. High genetic compatibility and optimal health."
        elif prob < 0.50 and thi > 72:
            return "Low Probability: Heat stress (High THI) is likely reducing fertility."
        elif prob < 0.50:
            return "Low Probability: Cow health indicators (BCS/Age) are likely suboptimal."
        return "Moderate chance. Monitor closely for standing heat."

# Test Block
if __name__ == "__main__":
    predictor = InseminationPredictor()
    test_data = {'semen_bull_code': 'FR_001_KUG'} # minimal test
    print(predictor.predict(test_data))