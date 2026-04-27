from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    telegram_bot_token: str
    telegram_mode: str = "polling"          # "polling" | "webhook"
    telegram_webhook_url: str = ""
    telegram_webhook_port: int = 8443
    agent_url: str = "http://localhost:8000"
    redis_url: str = "redis://redis:6379"


settings = Settings()
