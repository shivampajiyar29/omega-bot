"""
Application configuration — all providers wired in.
"""
from typing import List, Optional, Literal
import json
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "OmegaBot"
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me-in-production"
    DEBUG: bool = True

    # ─── PostgreSQL (Aiven Cloud) ──────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./omegabot.db"
    POSTGRES_SSL_MODE: str = "require"

    # ─── Redis (Redis Labs) ────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ─── InfluxDB ─────────────────────────────────────────────────────────────
    INFLUXDB_URL: Optional[str] = None
    INFLUXDB_TOKEN: Optional[str] = None
    INFLUXDB_ORG: Optional[str] = None
    INFLUXDB_BUCKET: str = "omegabot_ohlcv"

    # ─── MongoDB ──────────────────────────────────────────────────────────────
    MONGO_URL: Optional[str] = None
    MONGO_DB: str = "omegabot"

    # ─── Timescale fallback ────────────────────────────────────────────────────
    TIMESCALE_URL: Optional[str] = None

    # ─── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:13000",
        "http://127.0.0.1:13000",
    ]

    # ─── Groww ────────────────────────────────────────────────────────────────
    GROWW_ACCESS_TOKEN: Optional[str] = None
    GROWW_API_SECRET: Optional[str] = None
    GROWW_BASE_URL: str = "https://api.groww.in/v1"

    # ─── Binance ──────────────────────────────────────────────────────────────
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_API_SECRET: Optional[str] = None
    BINANCE_TESTNET: bool = False

    # ─── Zerodha ──────────────────────────────────────────────────────────────
    ZERODHA_API_KEY: Optional[str] = None
    ZERODHA_API_SECRET: Optional[str] = None
    ZERODHA_ACCESS_TOKEN: Optional[str] = None

    # ─── Upstox ───────────────────────────────────────────────────────────────
    UPSTOX_API_KEY: Optional[str] = None
    UPSTOX_API_SECRET: Optional[str] = None
    UPSTOX_ACCESS_TOKEN: Optional[str] = None

    # ─── Alpaca ───────────────────────────────────────────────────────────────
    ALPACA_API_KEY: Optional[str] = None
    ALPACA_API_SECRET: Optional[str] = None
    ALPACA_BASE_URL: str = "https://paper-api.alpaca.markets"

    # ─── AI Providers ─────────────────────────────────────────────────────────
    # Backward-compatible legacy name used in the repo today.
    # New UI/API should prefer DEFAULT_AI_PROVIDER + ENABLE_AI_FALLBACK.
    AI_PROVIDER: str = "gemini"  # gemini | nvidia | openrouter | anthropic | openai

    DEFAULT_AI_PROVIDER: Literal["openai", "anthropic", "perplexity", "gemini", "nvidia", "openrouter"] = "openai"
    ENABLE_AI_FALLBACK: bool = True

    GEMINI_API_KEY: Optional[str] = None

    NVIDIA_API_KEY: Optional[str] = None
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"

    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # Perplexity-compatible provider (OpenAI-compatible chat/completions surface).
    PERPLEXITY_API_KEY: Optional[str] = None
    PERPLEXITY_BASE_URL: str = "https://api.perplexity.ai"

    # ─── Notifications ────────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    TRADINGVIEW_WEBHOOK_SECRET: Optional[str] = None

    # ─── Trading Defaults ─────────────────────────────────────────────────────
    DEFAULT_TRADING_MODE: str = "paper"
    DEFAULT_BROKER: str = "groww"
    DEFAULT_MAX_DAILY_LOSS: float = 5000.0
    DEFAULT_MAX_TRADE_LOSS: float = 1000.0
    DEFAULT_MAX_POSITIONS: int = 10
    DEFAULT_MAX_ORDER_VALUE: float = 50000.0

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("[") and s.endswith("]"):
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, list):
                        return [str(i).strip() for i in parsed if str(i).strip()]
                except Exception:
                    pass
            return [i.strip() for i in s.split(",") if i.strip()]
        return v

    @model_validator(mode="after")
    def _sync_ai_provider_names(self):
        """
        Keep legacy AI_PROVIDER and new DEFAULT_AI_PROVIDER aligned.
        - If user sets AI_PROVIDER only, DEFAULT_AI_PROVIDER follows.
        - If user sets DEFAULT_AI_PROVIDER only, AI_PROVIDER follows.
        """
        legacy = (self.AI_PROVIDER or "").strip().lower()
        default = (self.DEFAULT_AI_PROVIDER or "").strip().lower()

        if legacy and not default:
            self.DEFAULT_AI_PROVIDER = legacy  # type: ignore[assignment]
        elif default and not legacy:
            self.AI_PROVIDER = default
        else:
            # Prefer explicit DEFAULT_AI_PROVIDER when both are set but disagree.
            if default and legacy and default != legacy:
                self.AI_PROVIDER = default
        return self

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def ai_enabled(self) -> bool:
        return any([
            self.GEMINI_API_KEY, self.NVIDIA_API_KEY,
            self.OPENROUTER_API_KEY, self.ANTHROPIC_API_KEY,
            self.OPENAI_API_KEY,
        ])

    @property
    def influx_enabled(self) -> bool:
        return bool(self.INFLUXDB_URL and self.INFLUXDB_TOKEN)

    @property
    def mongo_enabled(self) -> bool:
        return bool(self.MONGO_URL)


settings = Settings()
