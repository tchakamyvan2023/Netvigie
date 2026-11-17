"""
NETVIGIE — Configuration centralisée
Charge .env (via pydantic-settings) et config/netvigie.yaml.
"""
from pathlib import Path
from functools import lru_cache
from typing import List, Dict, Any

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Configuration chargée depuis .env"""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "NETVIGIE"
    app_env: str = "production"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_debug: bool = False
    app_secret_key: str = "change-me"

    # --- Frontend ---
    frontend_url: str = "http://192.168.1.40:3000"
    cors_origins: str = "http://192.168.1.40:3000,http://localhost:3000"

    # --- PostgreSQL ---
    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5432
    postgres_db: str = "netvigie"
    postgres_user: str = "netvigie"
    postgres_password: str = "Netvigie2026!"

    # --- Redis ---
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_db: int = 0

    # --- Wazuh API ---
    wazuh_api_url: str = "https://192.168.1.50:55000"
    wazuh_api_user: str = "wazuh"
    wazuh_api_password: str = "wazuh"
    wazuh_api_verify_ssl: bool = False

    # --- Wazuh Indexer ---
    wazuh_indexer_url: str = "https://192.168.1.50:9200"
    wazuh_indexer_user: str = "admin"
    wazuh_indexer_password: str = "admin"
    wazuh_indexer_verify_ssl: bool = False

    # --- Agents ---
    collector_interval_seconds: int = 10
    collector_alert_lookback_seconds: int = 300
    diagnostic_interval_seconds: int = 15
    diagnostic_ping_timeout_seconds: int = 2
    security_interval_seconds: int = 10
    correlation_interval_seconds: int = 20
    correlation_time_window_seconds: int = 60
    correlation_precedence_threshold_ms: int = 200

    # --- Auth ---
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # --- Admin initial ---
    admin_username: str = "admin"
    admin_email: str = "admin@netvigie.local"
    admin_password: str = "AdminNetvigie2026!"

    # --- Logs ---
    log_level: str = "INFO"
    log_dir: str = "./data/logs"

    @field_validator("cors_origins")
    @classmethod
    def split_cors(cls, v: str) -> str:
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


class NetvigieConfig:
    """Configuration métier chargée depuis config/netvigie.yaml"""

    def __init__(self, path: Path = PROJECT_ROOT / "config" / "netvigie.yaml"):
        self.path = path
        self.data: Dict[str, Any] = {}
        self._load()

    def _load(self):
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = yaml.safe_load(f) or {}
        else:
            self.data = {}

    @property
    def excluded_hosts(self) -> List[str]:
        return self.data.get("exclusions", {}).get("hosts", [])

    @property
    def thresholds(self) -> Dict[str, Any]:
        return self.data.get("thresholds", {})

    @property
    def correlation(self) -> Dict[str, Any]:
        return self.data.get("correlation", {})

    @property
    def retention(self) -> Dict[str, Any]:
        return self.data.get("retention", {})

    @property
    def machines_metadata(self) -> Dict[str, Any]:
        return self.data.get("machines_metadata", {})

    def is_excluded(self, ip: str = "", name: str = "") -> bool:
        """Vérifie si une machine est exclue (Kali, etc.)"""
        for h in self.excluded_hosts:
            if h == ip or h.lower() in name.lower():
                return True
        return False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


@lru_cache()
def get_netvigie_config() -> NetvigieConfig:
    return NetvigieConfig()


settings = get_settings()
netvigie_config = get_netvigie_config()