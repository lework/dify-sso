from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # 通用配置
    CONSOLE_WEB_URL: str = ""
    SECRET_KEY: str = "your-secret-key"
    TENANT_ID: str = ""
    EDITION: str = "SELF_HOSTED"
    
    # 刷新令牌配置
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: str = "30"
    REFRESH_TOKEN_PREFIX: str = "refresh_token:"
    ACCOUNT_REFRESH_TOKEN_PREFIX: str = "account_refresh_token:"

    # OIDC配置
    OIDC_ENABLED: bool = False
    OIDC_CLIENT_ID: str = ""
    OIDC_CLIENT_SECRET: str = ""
    OIDC_DISCOVERY_URL: str = ""
    OIDC_REDIRECT_URI: str = ""
    OIDC_SCOPE: str = "openid profile email"
    OIDC_RESPONSE_TYPE: str = "code"
    
    # 数据库配置
    DB_USERNAME: str = "dify_admin"
    DB_PASSWORD: str = "123456"
    DB_HOST: str = "127.0.0.1"
    DB_PORT: str = "5432"
    DB_DATABASE: str = "dify"
    
    # Redis配置
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: str = "6379"
    REDIS_DB: str = "0"
    REDIS_PASSWORD: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings() 