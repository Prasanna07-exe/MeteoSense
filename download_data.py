import requests
import pandas as pd

# Indian state + UT capitals (simplified list)
CITIES = [
    {"name": "Mumbai",        "lat": 18.9388, "lon": 72.8354},  # Maharashtra
    {"name": "Delhi",         "lat": 28.6139, "lon": 77.2090},  # NCT
    {"name": "Bengaluru",     "lat": 12.9716, "lon": 77.5946},  # Karnataka
    {"name": "Chennai",       "lat": 13.0827, "lon": 80.2707},  # Tamil Nadu
    {"name": "Kolkata",       "lat": 22.5726, "lon": 88.3639},  # West Bengal
    {"name": "Hyderabad",     "lat": 17.3850, "lon": 78.4867},  # Telangana
    {"name": "Ahmedabad",     "lat": 23.0225, "lon": 72.5714},  # Gujarat (Gandhinagar close by)
    {"name": "Jaipur",        "lat": 26.9124, "lon": 75.7873},  # Rajasthan
    {"name": "Lucknow",       "lat": 26.8467, "lon": 80.9462},  # Uttar Pradesh
    {"name": "Patna",         "lat": 25.5941, "lon": 85.1376},  # Bihar
    {"name": "Bhopal",        "lat": 23.2599, "lon": 77.4126},  # Madhya Pradesh
    {"name": "Bhubaneswar",   "lat": 20.2961, "lon": 85.8245},  # Odisha
    {"name": "Thiruvananthapuram","lat": 8.5241, "lon": 76.9366}, # Kerala
    {"name": "Kochi",         "lat": 9.9312,  "lon": 76.2673},  # Kerala major city
    {"name": "Chandigarh",    "lat": 30.7333, "lon": 76.7794},  # Punjab/Haryana/UT
    {"name": "Shimla",        "lat": 31.1048, "lon": 77.1734},  # Himachal Pradesh
    {"name": "Srinagar",      "lat": 34.0837, "lon": 74.7973},  # J&K
    {"name": "Leh",           "lat": 34.1526, "lon": 77.5770},  # Ladakh
    {"name": "Dehradun",      "lat": 30.3165, "lon": 78.0322},  # Uttarakhand
    {"name": "Ranchi",        "lat": 23.3441, "lon": 85.3096},  # Jharkhand
    {"name": "Raipur",        "lat": 21.2514, "lon": 81.6296},  # Chhattisgarh
    {"name": "Guwahati",      "lat": 26.1445, "lon": 91.7362},  # Assam (capital Dispur)
    {"name": "Agartala",      "lat": 23.8315, "lon": 91.2868},  # Tripura
    {"name": "Imphal",        "lat": 24.8170, "lon": 93.9368},  # Manipur
    {"name": "Shillong",      "lat": 25.5788, "lon": 91.8933},  # Meghalaya
    {"name": "Aizawl",        "lat": 23.7271, "lon": 92.7176},  # Mizoram
    {"name": "Kohima",        "lat": 25.6751, "lon": 94.1086},  # Nagaland
    {"name": "Itanagar",      "lat": 27.0844, "lon": 93.6053},  # Arunachal Pradesh
    {"name": "Gangtok",       "lat": 27.3389, "lon": 88.6065},  # Sikkim
    {"name": "Panaji",        "lat": 15.4909, "lon": 73.8278},  # Goa
    {"name": "Puducherry",    "lat": 11.9416, "lon": 79.8083},  # Puducherry UT
    {"name": "Port Blair",    "lat": 11.6234, "lon": 92.7265},  # Andaman & Nicobar
    {"name": "Kavaratti",     "lat": 10.5667, "lon": 72.6420},  # Lakshadweep
]

START_DATE = "2015-01-01"
END_DATE   = "2025-12-22"

def fetch_city_daily(city):
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": city["lat"],
        "longitude": city["lon"],
        "start_date": START_DATE,
        "end_date": END_DATE,
        "daily": "temperature_2m_max,temperature_2m_min,rain_sum,wind_speed_10m_max",
        "timezone": "Asia/Kolkata",
    }
    print(f"Fetching {city['name']}...")
    resp = requests.get(url, params=params)
    data = resp.json()

    # Basic error / missing-data checks
    if "daily" not in data:
        print(f"⚠ No 'daily' data for {city['name']}. Response keys: {list(data.keys())}")
        return None

    daily = pd.DataFrame({
        "date": pd.to_datetime(data["daily"]["time"]),
        "temp_max": data["daily"]["temperature_2m_max"],
        "temp_min": data["daily"]["temperature_2m_min"],
        "rain_sum": data["daily"]["rain_sum"],
        "wind_max": data["daily"]["wind_speed_10m_max"],
    })
    daily["city"] = city["name"]
    daily["lat"] = city["lat"]
    daily["lon"] = city["lon"]
    return daily


all_daily = []
for c in CITIES:
    daily = fetch_city_daily(c)
    if daily is not None and not daily.empty:
        all_daily.append(daily)
    else:
        print(f"⚠ Skipping {c['name']} due to missing data")

df_all = pd.concat(all_daily, ignore_index=True)
df_all.to_csv("india_capitals_daily_2015_2025.csv", index=False)
print("✅ Saved india_capitals_daily_2015_2025.csv shape:", df_all.shape)
