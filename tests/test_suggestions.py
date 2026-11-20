"""Tests for the weather, location and activity-idea rules (specs/activity-suggestions.md)."""

import pytest

from logic import (
    MAX_ACTIVITY_COST,
    MAX_SUGGESTIONS,
    parse_location,
    parse_weather,
    pick_client_ip,
    rule_suggestions,
    weather_kind,
)

# What Open-Meteo returned for Lisbon on a November afternoon (shortened).
OPEN_METEO = {
    "current": {"temperature_2m": 19.9, "weather_code": 3, "wind_speed_10m": 13.4, "is_day": 1},
    "daily": {"temperature_2m_max": [21.0], "precipitation_probability_max": [55]},
}

IPINFO = {"ip": "8.8.8.8", "city": "Lisbon", "country": "PT", "loc": "38.7223,-9.1393"}


def weather(kind="sunny", now=24.0, high=26.0, rain=0):
    return {"kind": kind, "temperature": now, "max_temperature": high, "rain_chance": rain, "wind": 10.0}


# --- Kind of weather -----------------------------------------------------------

@pytest.mark.parametrize("code, kind", [
    (0, "sunny"), (1, "sunny"), (2, "cloudy"), (3, "cloudy"), (45, "foggy"),
    (51, "rainy"), (63, "rainy"), (81, "rainy"), (71, "snowy"), (86, "snowy"), (95, "stormy"),
])
def test_weather_codes_have_a_kind(code, kind):
    assert weather_kind(code) == kind


def test_unknown_weather_code_is_rejected():
    with pytest.raises(ValueError):
        weather_kind(1234)


# --- Reading the weather -------------------------------------------------------

def test_weather_is_read_from_open_meteo():
    assert parse_weather(OPEN_METEO) == {
        "kind": "cloudy",
        "temperature": 19.9,
        "max_temperature": 21.0,
        "rain_chance": 55,
        "wind": 13.4,
    }


def test_weather_without_daily_values_still_works():
    result = parse_weather({"current": OPEN_METEO["current"]})
    assert result["max_temperature"] == 19.9
    assert result["rain_chance"] == 0


def test_weather_without_current_values_is_rejected():
    with pytest.raises(ValueError):
        parse_weather({"daily": OPEN_METEO["daily"]})


# --- Reading the location ------------------------------------------------------

def test_location_is_read_from_ipinfo():
    assert parse_location(IPINFO) == {"city": "Lisbon", "country": "PT", "lat": 38.7223, "lon": -9.1393}


def test_local_address_has_no_location():
    with pytest.raises(ValueError):
        parse_location({"ip": "127.0.0.1", "bogon": True})


def test_missing_location_is_rejected():
    with pytest.raises(ValueError):
        parse_location({"ip": "8.8.8.8", "city": "Lisbon"})


def test_broken_location_is_rejected():
    with pytest.raises(ValueError):
        parse_location({**IPINFO, "loc": "north of the river"})


def test_location_without_city_name_is_still_used():
    assert parse_location({**IPINFO, "city": ""})["city"] == "your area"


# --- Finding the visitor's IP address --------------------------------------------

def test_first_public_address_in_forwarded_header_is_used():
    assert pick_client_ip("10.0.0.4, 8.8.8.8, 1.1.1.1", "10.0.0.1") == "8.8.8.8"


def test_public_remote_address_is_used_without_header():
    assert pick_client_ip(None, "1.1.1.1") == "1.1.1.1"


def test_only_private_or_local_addresses_give_none():
    assert pick_client_ip("192.168.1.5, 127.0.0.1", "::1") is None


def test_nothing_known_gives_none():
    assert pick_client_ip(None, None) is None


def test_garbage_addresses_are_skipped():
    assert pick_client_ip("unknown, not-an-ip", "8.8.4.4") == "8.8.4.4"


# --- Ideas from the fixed rules --------------------------------------------------

def test_sunny_warm_day_suggests_the_beach_first():
    ideas = rule_suggestions(weather("sunny", high=26), [])
    assert ideas[0]["activity"] == "Beach day"


def test_rainy_day_suggests_only_inside_things():
    ideas = rule_suggestions(weather("rainy", now=16, high=17, rain=90), [])
    names = [idea["activity"] for idea in ideas]
    assert "Beach day" not in names
    assert "Board game evening" in names


def test_high_chance_of_rain_counts_as_wet():
    ideas = rule_suggestions(weather("cloudy", high=24, rain=80), [])
    assert "Beach day" not in [idea["activity"] for idea in ideas]


def test_cold_dry_day_suggests_no_beach():
    ideas = rule_suggestions(weather("sunny", now=8, high=12), [])
    assert "Beach day" not in [idea["activity"] for idea in ideas]


def test_mild_dry_day_suggests_outside_things():
    ideas = rule_suggestions(weather("cloudy", high=18, rain=10), [])
    assert "Picnic in the park" in [idea["activity"] for idea in ideas]


def test_rule_ideas_skip_what_is_already_on_the_list():
    ideas = rule_suggestions(weather("sunny", high=26), ["beach DAY"])
    assert "Beach day" not in [idea["activity"] for idea in ideas]


def test_rule_ideas_are_at_most_three_and_follow_the_rules():
    ideas = rule_suggestions(weather("sunny", high=26), [])
    assert 1 <= len(ideas) <= MAX_SUGGESTIONS
    for idea in ideas:
        assert 0 <= idea["cost"] <= MAX_ACTIVITY_COST
        assert idea["why"]
