from datetime import UTC, datetime, timedelta

from pydantic import BaseModel

from app.configs import config
from app.extensions.ext_database import db
from app.extensions.ext_redis import redis_client
from app.libs.helper import naive_utc_now
from app.models.account import (
    Account,
    AccountStatus,
)
from app.services.passport import PassportService
from app.services.token import TokenService


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    csrf_token: str


class AccountService:
    @staticmethod
    def _get_refresh_token_key(refresh_token: str) -> str:
        return f"{config.REFRESH_TOKEN_PREFIX}{refresh_token}"

    @staticmethod
    def _get_account_refresh_token_key(account_id: str) -> str:
        return f"{config.ACCOUNT_REFRESH_TOKEN_PREFIX}{account_id}"

    @staticmethod
    def store_refresh_token(refresh_token: str, account_id: str):
        redis_client.setex(AccountService._get_refresh_token_key(refresh_token), config.REFRESH_TOKEN_EXPIRE_DAYS,
                           account_id)
        redis_client.setex(
            AccountService._get_account_refresh_token_key(account_id), config.REFRESH_TOKEN_EXPIRE_DAYS, refresh_token
        )

    @staticmethod
    def get_account_jwt_token(account: Account) -> str:
        exp_dt = datetime.now(UTC) + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
        exp = int(exp_dt.timestamp())
        payload = {
            "user_id": account.id,
            "exp": exp,
            "iss": config.EDITION,
            "sub": "Console API Passport",
        }

        token: str = PassportService().issue(payload)
        return token

    @staticmethod
    def update_login_info(account: Account, *, ip_address: str):
        account.last_login_at = naive_utc_now()
        account.last_login_ip = ip_address
        db.session.add(account)
        db.session.commit()

    @staticmethod
    def login(account: Account, ip_address: str | None = None) -> TokenPair:
        if ip_address:
            AccountService.update_login_info(account=account, ip_address=ip_address)

        if account.status == AccountStatus.PENDING:
            account.status = AccountStatus.ACTIVE
            db.session.commit()

        access_token = AccountService.get_account_jwt_token(account=account)
        refresh_token = TokenService().generate_refresh_token()
        csrf_token = TokenService().generate_csrf_token(account.id)

        AccountService.store_refresh_token(refresh_token, account.id)

        return TokenPair(access_token=access_token, refresh_token=refresh_token, csrf_token=csrf_token)
