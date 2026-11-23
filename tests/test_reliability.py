"""Tests for keeping the app usable when something outside it fails (specs/reliability.md)."""

import json
import re
import tomllib
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy.exc import IntegrityError, InterfaceError, OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError

import db
import services
from logic import fund_label
from screens import safe

ROOT = Path(__file__).parent.parent
WEATHER_ANSWER = {"current": {"temperature_2m": 18, "weather_code": 3, "wind_speed_10m": 5}}
LOCATION_ANSWER = {"city": "Lisbon", "country": "PT", "loc": "38.72,-9.14"}


class FakeResponse:
    def __init__(self, data=None, status=200, bad_json=False):
        self.data, self.status, self.bad_json = data, status, bad_json

    def raise_for_status(self):
        if self.status >= 400:
            request = httpx.Request("GET", "https://example.com")
            raise httpx.HTTPStatusError("failed", request=request, response=httpx.Response(self.status, request=request))

    def json(self):
        if self.bad_json:
            raise json.JSONDecodeError("bad", "", 0)
        return self.data


class FakeNetwork:
    """Stands in for httpx.get, and counts the calls."""

    def __init__(self, answer):
        self.answer, self.calls, self.timeouts = answer, 0, []

    def __call__(self, _url, **kwargs):
        self.calls += 1
        self.timeouts.append(kwargs.get("timeout"))
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


@pytest.fixture
def clock(monkeypatch):
    """A clock the test can move forward."""
    now = {"t": 1000.0}
    monkeypatch.setattr(services.time, "monotonic", lambda: now["t"])
    return now


@pytest.fixture(autouse=True)
def fresh_services(monkeypatch):
    monkeypatch.setattr(services, "_down_until", {})


def use_network(monkeypatch, answer):
    network = FakeNetwork(answer)
    monkeypatch.setattr(services.httpx, "get", network)
    return network


# --- Weather and location services ------------------------------------------------


def test_working_service_answers(monkeypatch, clock):
    use_network(monkeypatch, FakeResponse(WEATHER_ANSWER))
    assert services.fetch_weather(38.7, -9.1)["temperature"] == 18


def test_working_service_is_asked_every_time(monkeypatch, clock):
    network = use_network(monkeypatch, FakeResponse(WEATHER_ANSWER))
    services.fetch_weather(38.7, -9.1)
    services.fetch_weather(38.7, -9.1)
    assert network.calls == 2


def test_requests_have_a_short_timeout(monkeypatch, clock):
    network = use_network(monkeypatch, FakeResponse(LOCATION_ANSWER))
    services.find_location("8.8.8.8")
    assert network.timeouts == [services.TIMEOUT]
    assert services.TIMEOUT <= 2


@pytest.mark.parametrize("failure", [
    httpx.ConnectTimeout("too slow"),
    httpx.ConnectError("no route"),
    FakeResponse(status=503),
    FakeResponse(bad_json=True),
])
def test_failed_service_is_not_asked_again_for_a_while(monkeypatch, clock, failure):
    network = use_network(monkeypatch, failure)
    for _ in range(3):
        with pytest.raises(ValueError):
            services.fetch_weather(38.7, -9.1)
    assert network.calls == 1


def test_failed_service_is_asked_again_after_the_wait(monkeypatch, clock):
    use_network(monkeypatch, httpx.ConnectTimeout("too slow"))
    with pytest.raises(ValueError):
        services.fetch_weather(38.7, -9.1)
    clock["t"] += services.RETRY_AFTER_SECONDS + 1
    use_network(monkeypatch, FakeResponse(WEATHER_ANSWER))
    assert services.fetch_weather(38.7, -9.1)["temperature"] == 18


def test_one_failed_service_does_not_block_the_other(monkeypatch, clock):
    use_network(monkeypatch, httpx.ConnectTimeout("too slow"))
    with pytest.raises(ValueError):
        services.fetch_weather(38.7, -9.1)
    use_network(monkeypatch, FakeResponse(LOCATION_ANSWER))
    assert services.find_location("8.8.8.8")["city"] == "Lisbon"


def test_private_address_is_not_an_outage(monkeypatch, clock):
    network = use_network(monkeypatch, FakeResponse({"ip": "127.0.0.1", "bogon": True}))
    for _ in range(2):
        with pytest.raises(ValueError):
            services.find_location("127.0.0.1")
    assert network.calls == 2


# --- A friendly message when the database cannot be reached -----------------------


@pytest.fixture
def screen(monkeypatch):
    shown = {"warnings": [], "buttons": []}
    monkeypatch.setattr(safe.st, "warning", lambda text, **_kwargs: shown["warnings"].append(text))
    monkeypatch.setattr(safe.st, "button", lambda text, **_kwargs: shown["buttons"].append(text))
    return shown


@pytest.mark.parametrize("error", [
    OperationalError("SELECT 1", {}, Exception("connection lost")),
    InterfaceError("SELECT 1", {}, Exception("connection closed")),
    PoolTimeoutError("no free connection"),
])
def test_connection_problem_shows_a_message(screen, error):
    with safe.database_guard():
        raise error
    assert screen["warnings"] == [safe.DATABASE_MESSAGE]


def test_message_has_a_button_only_when_asked(screen):
    error = OperationalError("SELECT 1", {}, Exception("connection lost"))
    with safe.database_guard():
        raise error
    assert screen["buttons"] == []
    with safe.database_guard(retry_button=True):
        raise error
    assert screen["buttons"] == ["Try again"]


def test_guard_works_on_a_function(screen):
    @safe.database_guard()
    def draw():
        raise OperationalError("SELECT 1", {}, Exception("connection lost"))

    draw()
    draw()
    assert len(screen["warnings"]) == 2


def test_nothing_is_shown_when_all_is_well(screen):
    with safe.database_guard():
        pass
    assert screen["warnings"] == []


@pytest.mark.parametrize("error", [
    ValueError("a rule was broken"),
    IntegrityError("INSERT", {}, Exception("duplicate")),
    KeyError("a bug"),
])
def test_other_errors_are_not_hidden(screen, error):
    with pytest.raises(type(error)):
        with safe.database_guard():
            raise error
    assert screen["warnings"] == []


def test_postgres_gives_up_connecting_after_a_few_seconds(monkeypatch):
    seen = {}
    postgres_engine = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
    monkeypatch.setattr(db, "create_engine", lambda url, **kwargs: seen.update(url=url, **kwargs) or postgres_engine)
    db.engine_from_url("postgresql://user:pass@example.com:5432/postgres")
    assert seen["url"].startswith("postgresql+psycopg://")
    assert seen["connect_args"] == {"connect_timeout": db.CONNECT_TIMEOUT_SECONDS}
    assert db.CONNECT_TIMEOUT_SECONDS <= 5


def test_sqlite_has_no_connect_timeout():
    engine = db.engine_from_url("sqlite://")
    assert engine.dialect.name == "sqlite"


# --- Words on the screen ----------------------------------------------------------


def test_saved_pant_entries_are_shown_as_deposit_money():
    assert fund_label("Pant") == "Deposit money"


@pytest.mark.parametrize("what", ["Pizza night", "Pants for the party", "pant"])
def test_other_descriptions_stay_as_typed(what):
    assert fund_label(what) == what


# --- Anyone can install and run the project ---------------------------------------


def test_locked_cryptography_has_a_package_for_intel_macs():
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    package = next(p for p in lock["package"] if p["name"] == "cryptography")
    wheels = [wheel["url"].rsplit("/", 1)[-1] for wheel in package["wheels"]]
    assert any("macosx" in name and ("x86_64" in name or "universal2" in name) for name in wheels)


def test_codespaces_uses_the_projects_python_and_packages():
    text = (ROOT / ".devcontainer" / "devcontainer.json").read_text()
    config = json.loads(re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE))
    needed = (ROOT / ".python-version").read_text().strip()
    assert f"python:1-{needed}-" in config["image"]
    assert "uv sync --frozen" in config["updateContentCommand"]
    assert config["postAttachCommand"]["server"].startswith("uv run --frozen streamlit run app.py")
