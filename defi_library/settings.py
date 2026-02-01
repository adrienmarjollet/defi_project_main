"""
Centralized configuration management using pydantic-settings.

This module provides type-safe, validated configuration loading from environment
variables and .env files. All settings are loaded once and cached.

Usage:
    from settings import get_settings

    settings = get_settings()
    rpc_url = settings.eth_rpc_url
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env_file() -> Path:
    """Find the .env file by searching up the directory tree."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        env_path = current / ".env"
        if env_path.exists():
            return env_path
        current = current.parent
    return Path(".env")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=_find_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Blockchain RPC
    eth_rpc_url: str = Field(
        ...,
        alias="ETH_RPC_URL",
        description="Ethereum RPC endpoint URL",
    )

    # API Keys
    etherscan_api_key: str = Field(
        ...,
        alias="ETHERSCAN_API_TOKEN",
        description="Etherscan API key for contract queries",
    )

    cmc_api_key: Optional[str] = Field(
        default=None,
        alias="CMC_API_KEY",
        description="CoinMarketCap API key (optional)",
    )

    chainstack_api_key: Optional[str] = Field(
        default=None,
        alias="CHAINSTACK_API_KEY",
        description="Chainstack API key for node discovery (optional)",
    )

    # Database
    database_url: str = Field(
        default="sqlite:///./data/requests_data/web3/web3_database.db",
        alias="DATABASE_URL",
        description="Database connection string",
    )

    postgres_url: Optional[str] = Field(
        default=None,
        alias="POSTGRES_URL",
        description="PostgreSQL connection string (optional)",
    )

    # Application settings
    log_level: str = Field(
        default="INFO",
        alias="LOG_LEVEL",
        description="Logging level",
    )

    cache_ttl_seconds: int = Field(
        default=3600,
        alias="CACHE_TTL_SECONDS",
        description="Cache time-to-live in seconds",
    )

    # Rate limiting
    requests_per_second: int = Field(
        default=5,
        alias="REQUESTS_PER_SECOND",
        description="API rate limit (requests per second)",
    )

    @field_validator("eth_rpc_url")
    @classmethod
    def validate_rpc_url(cls, v: str) -> str:
        """Ensure RPC URL is properly formatted."""
        if not v.startswith(("http://", "https://", "ws://", "wss://")):
            raise ValueError("RPC URL must start with http://, https://, ws://, or wss://")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is valid."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v_upper


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.

    Settings are loaded once from environment variables and .env file,
    then cached for subsequent calls.

    Returns:
        Settings: Application configuration object

    Raises:
        ValidationError: If required settings are missing or invalid
    """
    return Settings()


# Convenience function for backwards compatibility
def get_env_var(var_name: str) -> Optional[str]:
    """
    Get a single environment variable value.

    This is a convenience function for backwards compatibility.
    Prefer using get_settings() for type-safe access.

    Args:
        var_name: Name of the environment variable

    Returns:
        Value of the environment variable or None if not set
    """
    settings = get_settings()
    mapping = {
        "ETH_RPC_URL": settings.eth_rpc_url,
        "ETHERSCAN_API_TOKEN": settings.etherscan_api_key,
        "CMC_API_KEY": settings.cmc_api_key,
        "CHAINSTACK_API_KEY": settings.chainstack_api_key,
    }
    return mapping.get(var_name)
