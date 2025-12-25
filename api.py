from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import uvicorn
import requests
import pandas as pd
import numpy as np
import joblib
from datetime import date, datetime, timedelta
from typing import Any, Dict, List

WEATHER_BASE_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

app = FastAPI(title="Weather Model API")

# CORS for browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root_page():
    return RedirectResponse(url="/static/index.html")


# Load trained model
model = joblib.load("india_capitals_temperature_model.pkl")
feature_cols = joblib.load("india_model_features.pkl")


def fetch_weather(lat: float, lon: float) -> Dict[str, Any]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": "Asia/Kolkata",
        "current": (
            "temperature_2m,relative_humidity_2m,apparent_temperature,"
            "precipitation,weather_code,wind_speed_10m,wind_direction_10m"
        ),
        "hourly": (
            "temperature_2m,relative_humidity_2m,precipitation,"
            "precipitation_probability,weather_code,wind_speed_10m,wind_direction_10m"
        ),
        "daily": "temperature_2m_max,temperature_2m_min,weather_code",
        "forecast_days": 2,
        "past_days": 0,
    }
    resp = requests.get(WEATHER_BASE_URL, params=params)
    return resp.json()


def fetch_air_quality(lat: float, lon: float) -> Dict[str, Any]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": "Asia/Kolkata",
        "hourly": "pm10,pm2_5,european_aqi,us_aqi,carbon_monoxide,nitrogen_dioxide,ozone",
        "forecast_days": 1,
    }
    resp = requests.get(AIR_QUALITY_URL, params=params)
    return resp.json()


def describe_precip(weather_code: int, precip_mm: float) -> str:
    if precip_mm < 0.1:
        base = "No rain"
    elif precip_mm < 1.0:
        base = "Light rain"
    elif precip_mm < 4.0:
        base = "Moderate rain"
    else:
        base = "Heavy rain"

    if weather_code in (0, 1):
        return "Clear"
    if weather_code in (2, 3):
        return "Cloudy"
    if 51 <= weather_code <= 57:
        return "Drizzle"
    if 61 <= weather_code <= 67:
        return base
    if 71 <= weather_code <= 77:
        return "Snow"
    if 95 <= weather_code <= 99:
        return "Thunderstorms"
    return base


def get_daily_forecast(lat: float, lon: float) -> pd.DataFrame:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,rain_sum",
        "past_days": 40,
        "forecast_days": 2,
        "timezone": "Asia/Kolkata",
    }
    data = requests.get(url, params=params).json()
    daily = pd.DataFrame(data["daily"])
    daily["time"] = pd.to_datetime(daily["time"]).dt.date
    return daily


def build_features_for_tomorrow(daily: pd.DataFrame, lat: float, lon: float) -> pd.DataFrame:
    daily_sorted = daily.sort_values("time")
    today = date.today()
    day_yesterday = today - timedelta(days=1)
    day_before2 = today - timedelta(days=2)
    day_before3 = today - timedelta(days=3)

    lag1 = daily_sorted[daily_sorted["time"] == day_yesterday]
    lag2 = daily_sorted[daily_sorted["time"] == day_before2]
    lag3 = daily_sorted[daily_sorted["time"] == day_before3]

    if lag1.empty or lag2.empty or lag3.empty:
        last4 = daily_sorted.tail(4)
        lag1 = last4.iloc[-2:-1]
        lag2 = last4.iloc[-3:-2]
        lag3 = last4.iloc[-4:-3]

    temp_max_lag1 = float(lag1["temperature_2m_max"].iloc[0])
    temp_max_lag2 = float(lag2["temperature_2m_max"].iloc[0])
    temp_max_lag3 = float(lag3["temperature_2m_max"].iloc[0])
    rain_lag1 = float(lag1["rain_sum"].iloc[0])
    rain_lag3 = float(lag3["rain_sum"].iloc[0])

    last7 = daily_sorted.tail(7)
    last30 = daily_sorted.tail(30)
    temp_max_roll7_mean = float(last7["temperature_2m_max"].mean())
    temp_max_roll7_std = float(last7["temperature_2m_max"].std())
    temp_max_roll30_mean = float(last30["temperature_2m_max"].mean())
    rain_roll7_sum = float(last7["rain_sum"].sum())

    sin_day = np.sin(2 * np.pi * today.timetuple().tm_yday / 365.25)
    cos_day = np.cos(2 * np.pi * today.timetuple().tm_yday / 365.25)
    month = today.month

    city_id = 0  # simple placeholder

    X = pd.DataFrame([{
        "temp_max_lag1": temp_max_lag1,
        "temp_max_lag2": temp_max_lag2,
        "temp_max_lag3": temp_max_lag3,
        "rain_lag1": rain_lag1,
        "rain_lag3": rain_lag3,
        "temp_max_roll7_mean": temp_max_roll7_mean,
        "temp_max_roll30_mean": temp_max_roll30_mean,
        "temp_max_roll7_std": temp_max_roll7_std,
        "rain_roll7_sum": rain_roll7_sum,
        "sin_day": sin_day,
        "cos_day": cos_day,
        "month": month,
        "lat": lat,
        "lon": lon,
        "city_id": city_id,
    }])
    return X[feature_cols]  # ensure same column order


@app.get("/predict")
def predict(
    lat: float = Query(13.0827, description="Latitude"),
    lon: float = Query(80.2707, description="Longitude"),
    name: str = Query("Chennai", description="Location name"),
):
    daily = get_daily_forecast(lat, lon)
    daily_sorted = daily.sort_values("time")

    today = date.today()
    tomorrow = today + timedelta(days=1)

    row_tomorrow = daily_sorted[daily_sorted["time"] == tomorrow]
    if row_tomorrow.empty:
        row_tomorrow = daily_sorted.tail(1)

    provider_tomorrow = float(row_tomorrow["temperature_2m_max"].iloc[0])
    tomorrow_date = str(row_tomorrow["time"].iloc[0])

    X = build_features_for_tomorrow(daily, lat, lon)
    pred = float(model.predict(X)[0])

    return {
        "location_name": name,
        "lat": lat,
        "lon": lon,
        "tomorrow_date": tomorrow_date,
        "provider_forecast_c": provider_tomorrow,
        "ml_model_forecast_c": pred,
        "difference_c": pred - provider_tomorrow,
    }


@app.get("/full")
def full_weather(
    lat: float = Query(13.0827, description="Latitude"),
    lon: float = Query(80.2707, description="Longitude"),
    name: str = Query("Chennai", description="Location name"),
):
    w = fetch_weather(lat, lon)
    aq = fetch_air_quality(lat, lon)

    # current
    cur = w.get("current", {})
    current = {
        "time": cur.get("time"),
        "temp_c": cur.get("temperature_2m"),
        "feels_like_c": cur.get("apparent_temperature"),
        "humidity": cur.get("relative_humidity_2m"),
        "precip_mm_last": cur.get("precipitation"),
        "wind_kph": cur.get("wind_speed_10m"),
        "wind_deg": cur.get("wind_direction_10m"),
        "weather_code": cur.get("weather_code"),
    }
    current["precip_status"] = describe_precip(
        int(current["weather_code"] or 0),
        float(current["precip_mm_last"] or 0.0),
    )

    # hourly
    hourly_times = w["hourly"]["time"]
    hourly_temp = w["hourly"]["temperature_2m"]
    hourly_hum = w["hourly"]["relative_humidity_2m"]
    hourly_precip = w["hourly"]["precipitation"]
    hourly_pop = w["hourly"].get("precipitation_probability", [None] * len(hourly_times))
    hourly_wcode = w["hourly"]["weather_code"]
    hourly_wind = w["hourly"]["wind_speed_10m"]

    today_str = date.today().isoformat()
    tomorrow_str = (date.today() + timedelta(days=1)).isoformat()

    today_hourly: List[Dict[str, Any]] = []
    tomorrow_hourly: List[Dict[str, Any]] = []

    for t, T, H, P, POP, WC, W in zip(
        hourly_times, hourly_temp, hourly_hum, hourly_precip,
        hourly_pop, hourly_wcode, hourly_wind
    ):
        day = t[:10]
        item = {
            "time": t,
            "temp_c": T,
            "humidity": H,
            "precip_mm": P,
            "precip_prob": POP,
            "wind_kph": W,
            "weather_code": WC,
            "status": describe_precip(int(WC), float(P)),
        }
        if day == today_str:
            today_hourly.append(item)
        elif day == tomorrow_str:
            tomorrow_hourly.append(item)

    # daily summaries
    daily_w = w.get("daily", {})
    daily_times = daily_w.get("time", [])
    daily_max = daily_w.get("temperature_2m_max", [])
    daily_min = daily_w.get("temperature_2m_min", [])
    daily_wcode = daily_w.get("weather_code", [])

    today_summary = None
    tomorrow_summary = None
    for t, tmax, tmin, wc in zip(daily_times, daily_max, daily_min, daily_wcode):
        if t == today_str:
            today_summary = {
                "date": t,
                "max_c": tmax,
                "min_c": tmin,
                "status": describe_precip(int(wc), 0.0),
            }
        elif t == tomorrow_str:
            tomorrow_summary = {
                "date": t,
                "max_c": tmax,
                "min_c": tmin,
                "status": describe_precip(int(wc), 0.0),
            }

    # air quality (last hour)
    aq_hourly = aq.get("hourly", {})
    aq_times = aq_hourly.get("time", [])
    aq_us = aq_hourly.get("us_aqi", [])
    aq_pm25 = aq_hourly.get("pm2_5", [])

    air_quality = None
    if aq_times:
        air_quality = {
            "time": aq_times[-1],
            "us_aqi": aq_us[-1] if aq_us else None,
            "pm2_5": aq_pm25[-1] if aq_pm25 else None,
        }

    # ML model correction
    daily_for_model = get_daily_forecast(lat, lon)
    X_ml = build_features_for_tomorrow(daily_for_model, lat, lon)
    ml_max = float(model.predict(X_ml)[0])

        # Build model-style hourly temps for tomorrow by scaling API hourly temps
    # collect only real numbers, ignore None
    api_temps = [
        float(h["temp_c"])
        for h in tomorrow_hourly
        if h.get("temp_c") is not None
    ]

    if api_temps:
        api_max = max(api_temps)
        if api_max > 0:
            scale = ml_max / api_max
        else:
            scale = 1.0
    else:
        api_max = None
        scale = 1.0

    ml_hourly_temp = []
    for h in tomorrow_hourly:
        t = h.get("temp_c")
        if t is None or api_max is None:
            ml_hourly_temp.append(None)
        else:
            ml_hourly_temp.append(float(t) * scale)



    return {
        "location": {"name": name, "lat": lat, "lon": lon},
        "current": current,
        "air_quality": air_quality,
        "today": {
            "summary": today_summary,
            "hourly": today_hourly,
        },
        "tomorrow": {
            "summary": tomorrow_summary,
            "hourly": tomorrow_hourly,
            "ml_max_temp_c": ml_max,
            "ml_hourly_temp": ml_hourly_temp,
        },

    }


if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
