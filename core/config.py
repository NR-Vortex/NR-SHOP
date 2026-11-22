from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    BOT_TOKEN: SecretStr

    BOT_PROXY: str | None = None

    LOG_LEVEL: str = "INFO"

    # Database Settings
    POSTGRES_DB: str = "nr_shop"

    POSTGRES_USER: str = "nr_shop_user"

    POSTGRES_PASSWORD: SecretStr

    DB_HOST: str = "127.0.0.1"

    DB_PORT: int = 5432

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()