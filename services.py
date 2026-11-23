"""Calls to outside services: where the visitor is and the weather there.

Every function raises ValueError with a message for the screen when the service
cannot be reached or gives an answer we cannot use. The rules live in logic.py.
"""

import json
import time

import httpx

from logic import parse_location, parse_weather

TIMEOUT = 2.0  # seconds per step; the page waits for these calls
RETRY_AFTER_SECONDS = 120  # a service that failed is left alone this long, so clicks stay fast

_down_until: dict[str, float] = {}


def _get_json(service: str, url: str, problem: str, **kwargs) -> dict:
    """Ask a service for JSON. Raises ValueError(problem) if it fails or failed a moment ago."""
    if time.monotonic() < _down_until.get(service, 0):
        raise ValueError(problem)
    try:
        response = httpx.get(url, timeout=TIMEOUT, **kwargs)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, json.JSONDecodeError) as error:
        _down_until[service] = time.monotonic() + RETRY_AFTER_SECONDS
        raise ValueError(problem) from error


def find_location(ip: str | None) -> dict:
    """City and coordinates for an IP address (ipinfo.io, no key). Without an IP, the location of this computer."""
    url = f"https://ipinfo.io/{ip}/json" if ip else "https://ipinfo.io/json"
    return parse_location(_get_json("location", url, "Your location could not be found."))


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
    url = "https://api.open-meteo.com/v1/forecast"
    return parse_weather(_get_json("weather", url, "The weather is not available right now.", params=params))
