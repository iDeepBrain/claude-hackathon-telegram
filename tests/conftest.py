import os

# Set a placeholder token so `settings = Settings()` at module import time doesn't fail.
# Tests that need to test the missing-token case patch the env themselves inside pytest.raises.
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token-placeholder")
