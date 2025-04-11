import secrets
from datetime import timedelta
from app.utils.redis import redis_manager   
from app.core.config import settings

class TokenService:
    @staticmethod
    def generate_refresh_token() -> str:
        """生成refresh token"""
        return secrets.token_hex(64)

    @staticmethod
    def store_refresh_token(refresh_token: str, account_id: str) -> None:
        """存储refresh token到Redis"""
        refresh_token_key = f"{settings.REFRESH_TOKEN_PREFIX}{refresh_token}"
        account_refresh_token_key = f"{settings.ACCOUNT_REFRESH_TOKEN_PREFIX}{account_id}"

        # 设置过期时间
        REFRESH_TOKEN_EXPIRY = timedelta(days=int(settings.REFRESH_TOKEN_EXPIRE_DAYS))

        # 存储到Redis
        redis_manager.setex(refresh_token_key, REFRESH_TOKEN_EXPIRY, account_id)
        redis_manager.setex(account_refresh_token_key, REFRESH_TOKEN_EXPIRY, refresh_token)