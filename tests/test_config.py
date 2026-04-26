import pytest
from pydantic import ValidationError


def test_settings_loads_required_token(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token-123")
    monkeypatch.delenv("TELEGRAM_MODE", raising=False)
    monkeypatch.delenv("AGENT_URL", raising=False)
    import importlib
    import app.config as cfg_module
    importlib.reload(cfg_module)
    settings = cfg_module.Settings()
    assert settings.telegram_bot_token == "fake-token-123"


def test_settings_defaults():
    import importlib
    import app.config as cfg_module
    importlib.reload(cfg_module)
    from unittest.mock import patch
    with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "tok"}, clear=False):
        s = cfg_module.Settings()
    assert s.telegram_mode == "polling"
    assert s.agent_url == "http://localhost:8000"
    assert s.telegram_webhook_port == 8443
    assert s.telegram_webhook_url == ""


def test_settings_missing_token_raises():
    import importlib, os
    import app.config as cfg_module
    importlib.reload(cfg_module)
    env = {k: v for k, v in os.environ.items() if k != "TELEGRAM_BOT_TOKEN"}
    with pytest.raises((ValidationError, Exception)):
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict("os.environ", env, clear=True):
            cfg_module.Settings()
