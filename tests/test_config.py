import pytest
from unittest.mock import patch
from pydantic import ValidationError


def test_settings_loads_required_token():
    from app.config import Settings
    with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "fake-token-123"}, clear=True):
        s = Settings(_env_file=None)
    assert s.telegram_bot_token == "fake-token-123"


def test_settings_defaults():
    from app.config import Settings
    with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "tok"}, clear=True):
        s = Settings(_env_file=None)
    assert s.telegram_mode == "polling"
    assert s.agent_url == "http://localhost:8000"
    assert s.redis_url == "redis://redis:6379"
    assert s.telegram_webhook_port == 8443
    assert s.telegram_webhook_url == ""


def test_settings_missing_token_raises():
    from app.config import Settings
    with pytest.raises((ValidationError, Exception)):
        with patch.dict("os.environ", {}, clear=True):
            Settings(_env_file=None)


def test_settings_env_override():
    from app.config import Settings
    with patch.dict("os.environ", {
        "TELEGRAM_BOT_TOKEN": "tok",
        "AGENT_URL": "http://custom:9000",
        "REDIS_URL": "redis://custom:6380",
    }, clear=True):
        s = Settings(_env_file=None)
    assert s.agent_url == "http://custom:9000"
    assert s.redis_url == "redis://custom:6380"
