import os
from typing import Any
from urllib.parse import parse_qsl, quote_plus

from pydantic import Field, NonNegativeInt, PositiveInt, computed_field
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseSettings):
    DB_HOST: str = Field(
        description="Hostname or IP address of the database server.",
        default="localhost",
    )

    DB_PORT: PositiveInt = Field(
        description="Port number for database connection.",
        default=5432,
    )

    DB_USERNAME: str = Field(
        description="Username for database authentication.",
        default="postgres",
    )

    DB_PASSWORD: str = Field(
        description="Password for database authentication.",
        default="",
    )

    DB_DATABASE: str = Field(
        description="Name of the database to connect to.",
        default="dify",
    )

    DB_CHARSET: str = Field(
        description="Character set for database connection.",
        default="",
    )

    DB_EXTRAS: str = Field(
        description="Additional database connection parameters. Example: 'keepalives_idle=60&keepalives=1'",
        default="",
    )

    SQLALCHEMY_DATABASE_URI_SCHEME: str = Field(
        description="Database URI scheme for SQLAlchemy connection.",
        default="postgresql",
    )

    @computed_field
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        db_extras = (
            f"{self.DB_EXTRAS}&client_encoding={self.DB_CHARSET}" if self.DB_CHARSET else self.DB_EXTRAS
        ).strip("&")
        db_extras = f"?{db_extras}" if db_extras else ""
        return (
            f"{self.SQLALCHEMY_DATABASE_URI_SCHEME}://"
            f"{quote_plus(self.DB_USERNAME)}:{quote_plus(self.DB_PASSWORD)}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_DATABASE}"
            f"{db_extras}"
        )

    SQLALCHEMY_POOL_SIZE: NonNegativeInt = Field(
        description="Maximum number of database connections in the pool.",
        default=5,
    )

    SQLALCHEMY_MAX_OVERFLOW: NonNegativeInt = Field(
        description="Maximum number of connections that can be created beyond the pool_size.",
        default=5,
    )

    SQLALCHEMY_POOL_RECYCLE: NonNegativeInt = Field(
        description="Number of seconds after which a connection is automatically recycled.",
        default=3600,
    )

    SQLALCHEMY_POOL_USE_LIFO: bool = Field(
        description="If True, SQLAlchemy will use last-in-first-out way to retrieve connections from pool.",
        default=False,
    )

    SQLALCHEMY_POOL_PRE_PING: bool = Field(
        description="If True, enables connection pool pre-ping feature to check connections.",
        default=False,
    )

    SQLALCHEMY_ECHO: bool | str = Field(
        description="If True, SQLAlchemy will log all SQL statements.",
        default=False,
    )

    RETRIEVAL_SERVICE_EXECUTORS: NonNegativeInt = Field(
        description="Number of processes for the retrieval service, default to CPU cores.",
        default=os.cpu_count() or 1,
    )

    @computed_field  # type: ignore[misc]
    @property
    def SQLALCHEMY_ENGINE_OPTIONS(self) -> dict[str, Any]:
        # Parse DB_EXTRAS for 'options'
        db_extras_dict = dict(parse_qsl(self.DB_EXTRAS))
        options = db_extras_dict.get("options", "")
        # Always include timezone
        timezone_opt = "-c timezone=UTC"
        if options:
            # Merge user options and timezone
            merged_options = f"{options} {timezone_opt}"
        else:
            merged_options = timezone_opt

        connect_args = {"options": merged_options}

        return {
            "pool_size": self.SQLALCHEMY_POOL_SIZE,
            "max_overflow": self.SQLALCHEMY_MAX_OVERFLOW,
            "pool_recycle": self.SQLALCHEMY_POOL_RECYCLE,
            "pool_pre_ping": self.SQLALCHEMY_POOL_PRE_PING,
            "connect_args": connect_args,
            "pool_use_lifo": self.SQLALCHEMY_POOL_USE_LIFO,
        }
