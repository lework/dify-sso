import secrets
from datetime import timedelta

from app.configs import config
from app.extensions.ext_redis import redis_client


class TokenService:
    # 生成refresh token
    @staticmethod
    def generate_refresh_token() -> str:
        return secrets.token_hex(64)

    # 存储refresh token到Redis
    @staticmethod
    def store_refresh_token(refresh_token: str, account_id: str) -> None:
        refresh_token_key = f"{config.REFRESH_TOKEN_PREFIX}{refresh_token}"
        account_refresh_token_key = f"{config.ACCOUNT_REFRESH_TOKEN_PREFIX}{account_id}"

        # 设置过期时间
        REFRESH_TOKEN_EXPIRY = timedelta(days=int(config.REFRESH_TOKEN_EXPIRE_DAYS))

        # 存储到Redis
        redis_client.setex(refresh_token_key, REFRESH_TOKEN_EXPIRY, account_id)
        redis_client.setex(account_refresh_token_key, REFRESH_TOKEN_EXPIRY, refresh_token)