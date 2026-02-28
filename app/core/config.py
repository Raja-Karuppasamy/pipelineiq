from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    APP_NAME: str = "PipelineIQ"
    DEBUG: bool = False
    API_KEY_HEADER: str = "X-PipelineIQ-Key"
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_WEBHOOK_SECRET: str = ""
    ANTHROPIC_API_KEY: str = ""
    SLACK_BOT_TOKEN: str = ""
    SLACK_CHANNEL: str = "pipeline-alerts"
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_ID: str = ""
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "https://pipelineiq.dev"]

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
