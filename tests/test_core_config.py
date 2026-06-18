from __future__ import annotations

import os
from typing import Any, Dict

import pytest

from app.core import config


def _make_settings(**overrides: Any) -> config.Settings:
    base: Dict[str, Any] = {
        "DATABASE_URL": "sqlite+pysqlite:///:memory:",
    }
    base.update(overrides)
    return config.Settings(**base)


def test_settings_parse_cors_from_string():
    settings = _make_settings(
        BACKEND_CORS_ORIGINS="http://a.test, https://b.test , http://a.test",
    )
    assert settings.BACKEND_CORS_ORIGINS == [
        "http://a.test",
        "https://b.test",
        "http://a.test",
    ]


def test_settings_parse_cors_from_iterable():
    settings = _make_settings(BACKEND_CORS_ORIGINS=(" https://foo ", "bar"))
    assert settings.BACKEND_CORS_ORIGINS == ["https://foo", "bar"]


def test_settings_default_cors_allows_vite_localhost_and_loopback():
    settings = _make_settings()
    assert settings.BACKEND_CORS_ORIGINS == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_settings_parse_cors_none_returns_empty():
    settings = _make_settings(BACKEND_CORS_ORIGINS=None)
    assert settings.BACKEND_CORS_ORIGINS == []


def test_settings_parse_cors_invalid_type():
    with pytest.raises(TypeError):
        _make_settings(BACKEND_CORS_ORIGINS={"invalid"})


def test_settings_require_database_url():
    with pytest.raises(ValueError):
        _make_settings(DATABASE_URL="")


def test_get_settings_uses_cache_and_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "testing")
    try:
        config.get_settings.cache_clear()
        first = config.get_settings()
        second = config.get_settings()
    finally:
        config.get_settings.cache_clear()
        monkeypatch.delenv("APP_ENV", raising=False)

    assert first is second
    assert first.APP_ENV == "testing"
