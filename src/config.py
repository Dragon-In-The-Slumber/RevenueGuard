from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/revenueguard"
    redis_url: str = "redis://redis:6379/0"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
