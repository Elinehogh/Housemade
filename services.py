"""Calls to outside services: where the visitor is and the weather there.

Every function raises ValueError with a message for the screen when the service
cannot be reached or gives an answer we cannot use. The rules live in logic.py.
"""

import json

import httpx

from logic import parse_location, parse_weather

TIMEOUT = 5.0  # seconds; the page waits for these calls


def find_location(ip: str | None) -> dict:
    """City and coordinates for an IP address (ipinfo.io, no key). Without an IP, the location of this computer."""
    url = f"https://ipinfo.io/{ip}/json" if ip else "https://ipinfo.io/json"
    try:
        response = httpx.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        return parse_location(response.json())
    except (httpx.HTTPError, json.JSONDecodeError) as error:
        raise ValueError("Your location could not be found.") from error


def fetch_weather(lat: float, lon: float) -> dict:
    """Today's weather at a place (Open-Meteo, no key)."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,weather_code,wind_speed_10m",
        "daily": "temperature_2m_max,precipitation_probability_max",
        "forecast_days": 1,
        "timezone": "auto",
    }
    try:
        response = httpx.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=TIMEOUT)
        response.raise_for_status()
        return parse_weather(response.json())
    except (httpx.HTTPError, json.JSONDecodeError) as error:
        raise ValueError("The weather is not available right now.") from error
