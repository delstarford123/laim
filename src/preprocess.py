import pandas as pd
import numpy as np
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

class LivestockPreprocessor:
    def __init__(self):
        self.preprocessor = None
        
        # Define features based on standard dairy metrics
        # NOTE: We include the genetic stats here because train.py has already merged them in
        self.numeric_features = [
            'age_months', 'weight_kg', 'bcs_score', 
            'days_since_calving', 'milk_yield_daily', 'activity_index',
            'sire_fertility_score', 'straw_motility_percent'
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

    def fit_transform_save(self, data_path, save_path='models/preprocessor.joblib'):
        """
        Loads the ALREADY MERGED data, fits the preprocessor, and saves the artifact.
        """
        # Load the single merged CSV provided by train.py
        df = pd.read_csv(data_path)
        
        # Separate Target (Y) and Features (X)
        X = df.drop('conception_success', axis=1) 
        y = df['conception_success']

        # Fit the preprocessor
        print("⚙️  Fitting Transformation Pipeline...")
        self.build_pipeline()
        X_processed = self.preprocessor.fit_transform(X)
        
        # Save the processor logic
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        joblib.dump(self.preprocessor, save_path)
        print(f"✅ Preprocessor saved to {save_path}")
        
        return X_processed, y

if __name__ == "__main__":
    # Test block
    print("Preprocessor module loaded.")