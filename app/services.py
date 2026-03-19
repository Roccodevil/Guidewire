import os
from datetime import datetime

import requests


def _current_hour_decimal() -> float:
    now = datetime.now()
    return round(now.hour + (now.minute / 60), 2)


def get_tomtom_route_data(origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float) -> dict:
    api_key = os.getenv("TOMTOM_API_KEY")
    if not api_key or api_key == "your_tomtom_api_key_here":
        return {
            "status": "NO_ROUTE_FOUND",
            "delay_mins": 40.0,
            "is_severely_disrupted": True,
            "has_better_alternative": False,
            "live_speed_kph": 12.0,
            "route_deviation_km": 0.8,
            "historical_avg_speed_kph": 35.0,
            "time_of_day_hours": _current_hour_decimal(),
        }

    url = f"https://api.tomtom.com/routing/1/calculateRoute/{origin_lat},{origin_lon}:{dest_lat},{dest_lon}/json?key={api_key}&routeType=fastest&traffic=true"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        routes = data.get("routes", [])
        if not routes:
            return {
                "status": "NO_ROUTE_FOUND",
                "delay_mins": 0.0,
                "is_severely_disrupted": True,
                "has_better_alternative": False,
                "live_speed_kph": 0.0,
                "route_deviation_km": 0.0,
                "historical_avg_speed_kph": 25.0,
                "time_of_day_hours": _current_hour_decimal(),
            }

        primary_route = routes[0]
        summary = primary_route.get("summary", {})
        delay_mins = summary.get("trafficDelayInSeconds", 0) / 60.0
        length_km = summary.get("lengthInMeters", 0) / 1000.0
        travel_time_hours = max(summary.get("travelTimeInSeconds", 0) / 3600.0, 1 / 3600.0)
        live_speed_kph = round(length_km / travel_time_hours, 2) if length_km else 0.0

        route_deviation_km = round(min(delay_mins / 12.0, 5.0), 2)
        if len(routes) > 1:
            alt_summary = routes[1].get("summary", {})
            alt_length_km = alt_summary.get("lengthInMeters", 0) / 1000.0
            route_deviation_km = round(abs(alt_length_km - length_km), 2)

        historical_avg_speed_kph = round(max(live_speed_kph + (delay_mins * 0.75), 18.0), 2)

        return {
            "status": "ROUTE_CALCULATED",
            "delay_mins": delay_mins,
            "is_severely_disrupted": delay_mins > 30.0,
            "has_better_alternative": len(routes) > 1,
            "live_speed_kph": live_speed_kph,
            "route_deviation_km": route_deviation_km,
            "historical_avg_speed_kph": historical_avg_speed_kph,
            "time_of_day_hours": _current_hour_decimal(),
        }
    except Exception:
        return {
            "status": "API_ERROR",
            "delay_mins": 0.0,
            "is_severely_disrupted": False,
            "has_better_alternative": False,
            "live_speed_kph": 0.0,
            "route_deviation_km": 0.0,
            "historical_avg_speed_kph": 25.0,
            "time_of_day_hours": _current_hour_decimal(),
        }


def get_weather_forecast(lat: float, lon: float) -> dict:
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key or api_key == "your_openweather_api_key_here":
        return {"forecast": "Heavy Rain expected", "risk_multiplier": 1.5}

    url = (
        "https://api.openweathermap.org/data/2.5/forecast"
        f"?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    )
    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        high_risk = False
        for item in data.get("list", [])[:40]:
            weather_main = item.get("weather", [{}])[0].get("main", "Clear")
            temp = item.get("main", {}).get("temp", 25)
            if weather_main in ["Rain", "Thunderstorm", "Snow"] or temp > 42:
                high_risk = True
                break

        return {
            "forecast": "Extreme weather incoming" if high_risk else "Clear skies expected",
            "risk_multiplier": 1.5 if high_risk else 1.0,
        }
    except Exception:
        return {"forecast": "Unknown", "risk_multiplier": 1.0}
