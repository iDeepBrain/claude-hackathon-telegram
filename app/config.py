from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str
    telegram_mode: str = "polling"          # "polling" | "webhook"
    telegram_webhook_url: str = ""
    telegram_webhook_port: int = 8443
    agent_url: str = "http://localhost:8000"

    class Config:
        env_file = ".env"


settings = Settings()
