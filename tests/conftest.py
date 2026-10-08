"""Tests must never consume the operator's real keys or model configuration."""

from pathlib import Path

import pytest

from housing_app.settings import get_settings

DATABASE = Path(__file__).resolve().parents[1] / "data" / "housing.sqlite"


def pytest_collection_modifyitems(config, items):
    """Tests marked ``data`` need the private DB/CSV/model files; skip them where absent (CI)."""
    if DATABASE.is_file():
        return
    skip = pytest.mark.skip(reason="data/housing.sqlite not present")
    for item in items:
        if "data" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def isolate_api_settings(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("NAVER_MAPS_CLIENT_ID", "")
    monkeypatch.setenv("NAVER_MAPS_CLIENT_SECRET", "")
    monkeypatch.setenv("MAIN_MODEL", "gpt-6-luna")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
