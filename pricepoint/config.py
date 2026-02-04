"""Env Settings."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Env Settings."""

    # 1. Define individual components
    # These will be read from env vars like PRICEPOINT_POSTGRES_USER
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: SecretStr = SecretStr("postgres")
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "pricepoint"

    # Optional: If you want to force a specific driver (e.g., asyncpg, psycopg2)
    # default is standard 'postgresql'
    POSTGRES_SCHEME: str = "postgresql"

    class Config:
        """Settings Config."""

        # Pydantic will look for env vars starting with this prefix
        # Example: export PRICEPOINT_POSTGRES_SERVER=10.0.0.5
        env_prefix = "PRICEPOINT_"

        # This allows you to use .env files automatically if you want
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def database_url(self) -> str:
        """
        Constructs the SQLAlchemy/asyncpg connection string.

        Format: scheme://user:password@host:port/path
        """
        return (
            f"{self.POSTGRES_SCHEME}://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD.get_secret_value()}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/"
            f"{self.POSTGRES_DB}"
        )

    @property
    def database_url_async(self) -> str:
        """Helper for async connections (e.g. using asyncpg)."""
        return (
            f"postgresql+asyncpg://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD.get_secret_value()}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/"
            f"{self.POSTGRES_DB}"
        )


settings = Settings()
