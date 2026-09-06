from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Model provider ---
    # "auto" picks whichever key is present (Anthropic first, then Google).
    # Set explicitly to "anthropic" or "google" to pin one.
    llm_provider: str = "auto"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    google_api_key: str = ""
    google_model: str = "gemini-3.5-flash-lite"

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
    # Invoices processed concurrently per tick. Keep this low on a free-tier
    # model key: each invoice can make three model calls, so high concurrency
    # turns straight into 429s.
    #
    # Swapping to a paid key is configuration only — no code change:
    #   free tier : TICK_CONCURRENCY=3  DEMO_FAST=true   (~5 req/min quota)
    #   paid tier : TICK_CONCURRENCY=12 DEMO_FAST=false  (every invoice uses the model)
    tick_concurrency: int = 3
    # Retries for transient model failures (429/503).
    llm_max_retries: int = 4
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
    def active_provider(self) -> str:
        """
        Which provider to actually use.

        Resolved from configuration rather than assumed, so the same build runs on
        either vendor and can be switched back without a code change.
        """
        if self.llm_provider in ("anthropic", "google"):
            return self.llm_provider
        if self.anthropic_api_key:
            return "anthropic"
        if self.google_api_key:
            return "google"
        return "none"

    @property
    def active_model(self) -> str:
        return self.anthropic_model if self.active_provider == "anthropic" else self.google_model

    @property
    def llm_api_key(self) -> str:
        provider = self.active_provider
        if provider == "anthropic":
            return self.anthropic_api_key
        if provider == "google":
            return self.google_api_key
        return ""

    @property
    def razorpay_configured(self) -> bool:
        return bool(self.razorpay_key_id and self.razorpay_key_secret)


settings = Settings()
