import requests
import pandas as pd
import os
import time
from datetime import datetime

# --- CONFIGURATION ---
CSV_FILE = 'data/weather_data.csv'
UPDATE_INTERVAL_SECONDS = 10  # Updates every 10 seconds

# Pre-defined list of 10 nearby counties
NEARBY_COUNTIES = {
    "Kakamega": {"lat": 0.2827, "lon": 34.7519},
    "Bungoma":  {"lat": 0.5695, "lon": 34.5584},
    "Busia":    {"lat": 0.4608, "lon": 34.1115},
    "Vihiga":   {"lat": 0.0768, "lon": 34.7223},
    "Kisumu":   {"lat": -0.0917, "lon": 34.7680},
    "Siaya":    {"lat": 0.0623, "lon": 34.2882},
    "Nandi":    {"lat": 0.1833, "lon": 35.0000},
    "Uasin Gishu": {"lat": 0.5143, "lon": 35.2698},
    "Trans Nzoia": {"lat": 1.0157, "lon": 35.0062},
    "Kericho":  {"lat": -0.3689, "lon": 35.2863}
}

def get_user_location():
    """Attempts to auto-detect the user's current location based on IP."""
    try:
        response = requests.get("http://ip-api.com/json/", timeout=5)
        data = response.json()
        if data['status'] == 'success':
            return {
                "name": f"My Location ({data['city']})",
                "lat": data['lat'],
                "lon": data['lon']
            }
    except Exception:
        pass
    return {"name": "User Default (Kakamega)", "lat": 0.2827, "lon": 34.7519}

def calculate_thi(temp_c, humidity_percent):
    """Calculates Temperature-Humidity Index (THI)."""
    rh_decimal = humidity_percent / 100.0
    thi = (0.8 * temp_c) + (rh_decimal * (temp_c - 14.4)) + 46.4
    return round(thi, 1)

def fetch_weather(lat, lon):
    """Fetches real-time weather from Open-Meteo API."""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m",
            "timezone": "auto"
        }
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data['current']
    except Exception as e:
        print(f"❌ API Error: {e}")
        return None

def update_cycle():
    """Runs one full update cycle, OVERWRITING existing locations."""
    print(f"\n🔄 Updating: {datetime.now().strftime('%H:%M:%S')}")
    
    # 1. Get User Location & Combine
    user_loc = get_user_location()
    all_locations = NEARBY_COUNTIES.copy()
    all_locations[user_loc['name']] = {"lat": user_loc['lat'], "lon": user_loc['lon']}

    # 2. Load existing CSV safely
    cols = ['timestamp', 'location', 'avg_temp_c', 'humidity_percent', 'thi_index']
    
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            # Check if file was empty or missing columns
            if df.empty or 'location' not in df.columns:
                df = pd.DataFrame(columns=cols)
        except pd.errors.EmptyDataError:
            # File exists but is empty -> Create new
            df = pd.DataFrame(columns=cols)
    else:
        df = pd.DataFrame(columns=cols)

    # 3. Loop through locations and UPDATE the DataFrame
    for place_name, coords in all_locations.items():
        weather = fetch_weather(coords['lat'], coords['lon'])
        
        if weather:
            thi = calculate_thi(weather['temperature_2m'], weather['relative_humidity_2m'])
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Check if this location is already in the CSV
            if place_name in df['location'].values:
                # UPDATE existing row
                mask = df['location'] == place_name
                df.loc[mask, 'timestamp'] = timestamp
                df.loc[mask, 'avg_temp_c'] = weather['temperature_2m']
                df.loc[mask, 'humidity_percent'] = weather['relative_humidity_2m']
                df.loc[mask, 'thi_index'] = thi
                print(f"   Refreshed: {place_name} ({thi})")
            else:
                # ADD new row
                new_row = pd.DataFrame([{
                    'timestamp': timestamp,
                    'location': place_name,
                    'avg_temp_c': weather['temperature_2m'],
                    'humidity_percent': weather['relative_humidity_2m'],
                    'thi_index': thi
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                print(f"   Added: {place_name} ({thi})")

    # 4. Save the CLEAN DataFrame back to CSV
    df.to_csv(CSV_FILE, index=False)
    print("💾 File saved.")
    # 4. Save the CLEAN DataFrame back to CSV
    df.to_csv(CSV_FILE, index=False)
    print("💾 File saved.")

if __name__ == "__main__":
    os.makedirs('data', exist_ok=True)
    print(f"🚀 Live Monitor Started (Updates every {UPDATE_INTERVAL_SECONDS}s). Press Ctrl+C to stop.")
    
    # Clean start: Delete old messy file if needed
    # if os.path.exists(CSV_FILE): os.remove(CSV_FILE)

    try:
        while True:
            update_cycle()
            time.sleep(UPDATE_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\n🛑 Monitor Stopped.")