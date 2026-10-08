"""Tests must never consume the operator's real keys or model configuration."""

import pytest


@pytest.fixture(autouse=True)
def isolate_api_settings(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("NAVER_MAPS_CLIENT_ID", "")
    monkeypatch.setenv("NAVER_MAPS_CLIENT_SECRET", "")
    monkeypatch.setenv("MAIN_MODEL", "gpt-6-luna")
