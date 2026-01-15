import requests
import pandas as pd
import os
from datetime import datetime

# --- CONFIGURATION ---
# Default to Kakamega, Kenya (You can change this)
LATITUDE = 0.2827
LONGITUDE = 34.7519
CSV_FILE = 'data/weather_data.csv'

def calculate_thi(temp_c, humidity_percent):
    """
    Calculates Temperature-Humidity Index (THI) for cattle.
    Formula: NRC (1971) adapted for Celsius.
    """
    # 1.8 * T + 32 converts C to F for the standard formula part
    # THI = (1.8 × Tdb + 32) − [(0.55 − 0.0055 × RH) × (1.8 × Tdb − 26)]
    rh_decimal = humidity_percent / 100.0
    # THI = (1.8 * temp_c + 32) - ((0.55 - 0.0055 * humidity_percent) * (1.8 * temp_c - 26))
    
    # Simpler widely used approximation:
    # THI = 0.8 * T + RH * (T - 14.4) + 46.4
    thi = (0.8 * temp_c) + (rh_decimal * (temp_c - 14.4)) + 46.4
    return round(thi, 1)

def fetch_current_weather():
    """Fetches real-time weather from Open-Meteo API"""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
            "current": "temperature_2m,relative_humidity_2m",
            "timezone": "auto"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status() # Check for API errors
        data = response.json()
        
        current = data['current']
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'avg_temp_c': current['temperature_2m'],
            'humidity_percent': current['relative_humidity_2m']
        }
    except Exception as e:
        print(f"❌ Error fetching weather: {e}")
        return None

def update_csv():
    """Updates the CSV file with today's weather"""
    weather = fetch_current_weather()
    
    if not weather:
        return

    # Calculate THI
    thi = calculate_thi(weather['avg_temp_c'], weather['humidity_percent'])
    
    new_row = {
        'date': weather['date'],
        'avg_temp_c': weather['avg_temp_c'],
        'humidity_percent': weather['humidity_percent'],
        'thi_index': thi
    }

    # Load existing CSV or create new
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
    else:
        df = pd.DataFrame(columns=['date', 'avg_temp_c', 'humidity_percent', 'thi_index'])

    # Check if today's date already exists to avoid duplicates
    if weather['date'] in df['date'].values:
        print(f"⚠️ Weather for {weather['date']} already exists. Updating it...")
        # Update the existing row
        df.loc[df['date'] == weather['date'], ['avg_temp_c', 'humidity_percent', 'thi_index']] = \
            [weather['avg_temp_c'], weather['humidity_percent'], thi]
    else:
        # Append new row
        new_df = pd.DataFrame([new_row])
        df = pd.concat([df, new_df], ignore_index=True)
        print(f"✅ Added new weather data for {weather['date']}")

    # Save back to CSV
    df.to_csv(CSV_FILE, index=False)
    print(f"🌡️ Current Status: {weather['avg_temp_c']}°C, Humidity: {weather['humidity_percent']}%, THI: {thi}")

if __name__ == "__main__":
    # Ensure data folder exists
    os.makedirs('data', exist_ok=True)
    update_csv()