import pandas as pd
import numpy as np
import joblib
import os
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

class LivestockPreprocessor:
    def __init__(self):
        self.preprocessor = None
        
        # --- UPDATED: Added Weather Metrics to Numeric Features ---
        self.numeric_features = [
            'age_months', 'weight_kg', 'bcs_score', 
            'days_since_calving', 'milk_yield_daily', 'activity_index',
            'sire_fertility_score', 'straw_motility_percent',
            # NEW WEATHER FEATURES
            'avg_temp_c', 'humidity_percent', 'thi_index'
        ]
        
        # Categorical features
        self.categorical_features = ['breed', 'parity', 'semen_bull_code']
       
    def build_pipeline(self):
        """Creates the transformation pipeline."""
        
        # 1. Handle Numbers: Impute missing with median, then scale
        numeric_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler())
        ])

        # 2. Handle Text: Impute missing, then OneHotEncode
        categorical_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
            ('onehot', OneHotEncoder(handle_unknown='ignore'))
        ])

        # Combine them
        self.preprocessor = ColumnTransformer(
            transformers=[
                ('num', numeric_transformer, self.numeric_features),
                ('cat', categorical_transformer, self.categorical_features)
            ])
            
        return self.preprocessor

    def _enrich_with_weather(self, df):
        """
        Internal helper: Loads weather_data.csv and adds climate context.
        Since historical farm data might lack dates, we apply the 
        average regional weather from our logs to the training set.
        """
        weather_path = 'data/weather_data.csv'
        
        try:
            if os.path.exists(weather_path):
                weather_df = pd.read_csv(weather_path)
                
                # Calculate averages from the logs
                avg_temp = weather_df['avg_temp_c'].mean()
                avg_hum = weather_df['humidity_percent'].mean()
                avg_thi = weather_df['thi_index'].mean()
                
                print(f"🌦️  Enriching training data with Weather Context (Avg THI: {avg_thi:.1f})")
                
                # Assign these values to the entire dataset
                # (In a real advanced system, you would join on Date/Location)
                df['avg_temp_c'] = avg_temp
                df['humidity_percent'] = avg_hum
                df['thi_index'] = avg_thi
                
            else:
                print("⚠️ Weather data not found. Using defaults.")
                # Fallback defaults (Kakamega averages)
                df['avg_temp_c'] = 24.0
                df['humidity_percent'] = 60.0
                df['thi_index'] = 72.0
                
        except Exception as e:
            print(f"⚠️ Error loading weather data: {e}")
            # Fallback on error to prevent crash
            df['avg_temp_c'] = 24.0
            df['humidity_percent'] = 60.0
            df['thi_index'] = 72.0
            
        return df

    def fit_transform_save(self, data_path, save_path='models/preprocessor.joblib'):
        """
        Loads data, ENRICHES it with weather, fits preprocessor, and saves.
        """
        # Load the primary farm data
        df = pd.read_csv(data_path)
        
        # --- NEW: Enrich with Weather Data ---
        df = self._enrich_with_weather(df)
        
        # Separate Target (Y) and Features (X)
        # Check if conception_success exists (it should for training)
        if 'conception_success' in df.columns:
            X = df.drop('conception_success', axis=1) 
            y = df['conception_success']
        else:
            # Handle edge case if passed data without target
            X = df
            y = None

        # Fit the preprocessor
        print("⚙️  Fitting Transformation Pipeline...")
        self.build_pipeline()
        
        # Fit and Transform
        X_processed = self.preprocessor.fit_transform(X)
        
        # Save the processor logic
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        joblib.dump(self.preprocessor, save_path)
        print(f"✅ Preprocessor saved to {save_path}")
        
        return X_processed, y

if __name__ == "__main__":
    # Test block
    print("Preprocessor module loaded.")