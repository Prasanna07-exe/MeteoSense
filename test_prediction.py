import requests
import pandas as pd
import numpy as np
import joblib
from datetime import datetime

print("🔄 Loading model...")
model = joblib.load('temperature_model.pkl')
features = joblib.load('model_features.pkl')

print("🌤️ Getting live Chennai forecast...")
LAT, LON = 13.0827, 80.2707
url = "https://api.open-meteo.com/v1/forecast"
params = {
    "latitude": LAT, "longitude": LON,
    "daily": "temperature_2m_max,temperature_2m_min,rain_sum",
    "past_days": 3,
    "timezone": "Asia/Kolkata"
}

data = requests.get(url, params=params).json()
daily = pd.DataFrame(data["daily"])

today = datetime.now().date()

features_df = pd.DataFrame({
    "temp_max_lag1": [daily["temperature_2m_max"].iloc[-2]],
    "temp_max_lag2": [daily["temperature_2m_max"].iloc[-3]],
    "rain_lag1": [daily["rain_sum"].iloc[-2]],
    "sin_day": [np.sin(2 * np.pi * today.timetuple().tm_yday / 365.25)],
    "cos_day": [np.cos(2 * np.pi * today.timetuple().tm_yday / 365.25)],
    "month": [today.month],
})

prediction = model.predict(features_df)[0]
provider_tomorrow = daily["temperature_2m_max"].iloc[-1]

print("\n🎯 RESULTS:")
print(f"📅 Tomorrow:           {today + pd.Timedelta(days=1):%Y-%m-%d}")
print(f"🌡️ Provider forecast:  {provider_tomorrow:.1f} °C")
print(f"🤖 Your ML model:      {prediction:.1f} °C")
print(f"📊 Difference:         {prediction - provider_tomorrow:+.1f} °C")
