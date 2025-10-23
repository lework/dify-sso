from pydantic_settings import SettingsConfigDict

from .app_config import AppConfig
from .database_config import DatabaseConfig
from .logger_config import LoggingConfig
from .redis_config import RedisConfig
from .sso_config import SSOConfig


class Config(
    AppConfig,
    DatabaseConfig,
    RedisConfig,
    LoggingConfig,
    SSOConfig,
):
    model_config = SettingsConfigDict(
        # read from dotenv format config file
        env_file=".env",
        env_file_encoding="utf-8",
        # ignore extra attributes
        extra="ignore",
    )


config = Config()
