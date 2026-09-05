from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    anthropic_api_key: str = ""

    # --- Razorpay ---
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    # Secret configured on the Razorpay webhook, used to verify X-Razorpay-Signature.
    razorpay_webhook_secret: str = ""
    # Public base URL used as the payment-link callback.
    public_url: str = "http://localhost:8000"

    # --- Access control ---
    # Shared secret for destructive/simulation endpoints. Empty disables the check,
    # which is the local-dev default; set it in any deployed environment.
    demo_token: str = ""
    # Comma-separated allowed origins. "*" cannot be combined with credentials.
    cors_origins: str = "http://localhost:3000"

    # --- Performance ---
    # Invoices processed concurrently per tick.
    tick_concurrency: int = 8
    # In DEMO_FAST, only hero clients use live Claude; the rest use the deterministic
    # path. Keeps a 100-invoice run inside a demo slot without faking the hero cases.
    demo_fast: bool = True
    sql_echo: bool = False

    # --- Notifications ---
    slack_webhook_url: str = ""

    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/revenueguard"
    redis_url: str = "redis://redis:6379/0"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def razorpay_configured(self) -> bool:
        return bool(self.razorpay_key_id and self.razorpay_key_secret)


settings = Settings()
