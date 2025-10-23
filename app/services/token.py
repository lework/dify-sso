import secrets
from datetime import UTC, datetime, timedelta

from werkzeug.wrappers import Response

from app.configs import config
from app.extensions.ext_redis import redis_client
from app.services.passport import PassportService

COOKIE_NAME_ACCESS_TOKEN = "access_token"
COOKIE_NAME_REFRESH_TOKEN = "refresh_token"
COOKIE_NAME_CSRF_TOKEN = "csrf_token"


class TokenService:
    @staticmethod
    def is_secure() -> bool:
        url = str(config.CONSOLE_WEB_URL)
        return url.startswith("https") if url else False

    @staticmethod
    def real_cookie_name(cookie_name: str) -> str:
        return "__Host-" + cookie_name if TokenService.is_secure() else cookie_name

    # 生成refresh token
    @staticmethod
    def generate_refresh_token() -> str:
        return secrets.token_hex(64)

    @staticmethod
    def generate_csrf_token(user_id: str) -> str:
        exp_dt = datetime.now(UTC) + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "exp": int(exp_dt.timestamp()),
            "sub": user_id,
        }
        return PassportService().issue(payload)

    # 存储refresh token到Redis
    @staticmethod
    def store_refresh_token(refresh_token: str, account_id: str) -> None:
        refresh_token_key = f"{config.REFRESH_TOKEN_PREFIX}{refresh_token}"
        account_refresh_token_key = f"{config.ACCOUNT_REFRESH_TOKEN_PREFIX}{account_id}"

        # 设置过期时间
        refresh_token_expiry = timedelta(days=int(config.REFRESH_TOKEN_EXPIRE_DAYS))

        # 存储到Redis
        redis_client.setex(refresh_token_key, refresh_token_expiry, account_id)
        redis_client.setex(account_refresh_token_key, refresh_token_expiry, refresh_token)

    @staticmethod
    def set_access_token_to_cookie(response: Response, token: str, samesite: str = "Lax"):
        response.set_cookie(
            TokenService.real_cookie_name(COOKIE_NAME_ACCESS_TOKEN),
            value=token,
            httponly=True,
            secure=TokenService.is_secure(),
            samesite=samesite,
            max_age=int(config.ACCESS_TOKEN_EXPIRE_MINUTES * 60),
            path="/"
        )

    @staticmethod
    def set_refresh_token_to_cookie(response: Response, token: str):
        response.set_cookie(
            TokenService.real_cookie_name(COOKIE_NAME_REFRESH_TOKEN),
            value=token,
            httponly=True,
            secure=TokenService.is_secure(),
            samesite="Lax",
            max_age=int(60 * 60 * 24 * config.REFRESH_TOKEN_EXPIRE_DAYS),
            path="/"
        )

    @staticmethod
    def set_csrf_token_to_cookie(response: Response, token: str):
        response.set_cookie(
            TokenService.real_cookie_name(COOKIE_NAME_CSRF_TOKEN),
            value=token,
            httponly=False,
            secure=TokenService.is_secure(),
            samesite="Lax",
            max_age=int(60 * config.ACCESS_TOKEN_EXPIRE_MINUTES),
            path="/"
        )
