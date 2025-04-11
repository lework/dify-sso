import requests
from urllib.parse import urlencode
from typing import Dict
from sqlalchemy.orm import Session
from datetime import UTC, datetime, timedelta
import logging

from app.core.config import settings
from .passport import PassportService
from .token import TokenService
from app.models.account import Account, AccountStatus

logger = logging.getLogger(__name__)

class OIDCService:
    def __init__(self):
        self.client_id = settings.OIDC_CLIENT_ID
        self.client_secret = settings.OIDC_CLIENT_SECRET
        self.discovery_url = settings.OIDC_DISCOVERY_URL
        self.redirect_uri = settings.OIDC_REDIRECT_URI
        self.scope = settings.OIDC_SCOPE
        self.response_type = settings.OIDC_RESPONSE_TYPE
        self.tenant_id = settings.TENANT_ID
        self.passport_service = PassportService()
        self.token_service = TokenService()
        
        # 获取OIDC配置
        self._load_oidc_config()
    
    def _load_oidc_config(self):
        """加载OIDC配置"""
        response = requests.get(self.discovery_url)
        if response.status_code == 200:
            config = response.json()
            self.authorization_endpoint = config.get('authorization_endpoint')
            self.token_endpoint = config.get('token_endpoint')
            self.userinfo_endpoint = config.get('userinfo_endpoint')
        else:
            raise Exception("Failed to load OIDC configuration")

    def check_oidc_config(self) -> bool:
        if not self.authorization_endpoint or not self.token_endpoint or not self.userinfo_endpoint:
            return False
        return True

    def get_login_url(self) -> str:
        """生成登录URL"""
        params = {
            'client_id': self.client_id,
            'response_type': self.response_type,
            'scope': self.scope,
            'redirect_uri': self.redirect_uri,
            'state': 'random_state'  # 实际应用中应该使用随机生成的状态
        }
        return f"{self.authorization_endpoint}?{urlencode(params)}"

    def get_token(self, code: str) -> Dict:
        """获取访问令牌"""
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        response = requests.post(self.token_endpoint, data=data)
        if response.status_code != 200:
            logger.exception("获取token失败: status_code=%d, response=%s", 
                           response.status_code, response.text)
            raise Exception("Failed to get token")
        return response.json()

    def get_user_info(self, access_token: str) -> Dict:
        """获取用户信息"""
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(self.userinfo_endpoint, headers=headers)
        if response.status_code != 200:
            logger.exception("获取用户信息失败: status_code=%d, response=%s", 
                           response.status_code, response.text)
            raise Exception("Failed to get user info")
        return response.json()

    def handle_callback(self, code: str, db: Session, client_host: str) -> Dict[str, str]:
        """处理回调，返回access token和refresh token"""
        # 获取访问令牌
        token_response = self.get_token(code)
        access_token = token_response.get('access_token')
        
        # 获取用户信息
        user_info = self.get_user_info(access_token)
        user_name = user_info.get('name')
        user_email = user_info.get('email')

        # 查找系统用户
        account = Account.get_by_email(db, user_email)

        # 如果系统用户不存在，则创建系统用户
        if not account:
            account = Account.create(
                db=db,
                email=user_email,
                name=user_name,
                avatar="",
                tenant_id=self.tenant_id
            )
            logger.info("创建用户: %s", user_email)


        # 更新用户登录信息
        account.last_login_at = datetime.now(UTC)
        account.last_login_ip = client_host
        if account.status != AccountStatus.ACTIVE:
            account.status = AccountStatus.ACTIVE
        if account.name != user_name:
            account.name = user_name
        db.commit()

        logger.info("用户验证成功: %s", user_email)
        
        # 生成JWT token
        exp_dt = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        exp = int(exp_dt.timestamp())
        account_id = str(account.id)
        payload = {
            "user_id": account_id,  # 将UUID转换为字符串
            "exp": exp,
            "iss": settings.EDITION,
            "sub": "Console API Passport",
        }

        # 生成access token
        console_access_token: str = self.passport_service.issue(payload)

        # 生成并存储refresh token
        refresh_token = self.token_service.generate_refresh_token()
        self.token_service.store_refresh_token(refresh_token, account_id)

        return {
            "access_token": console_access_token,
            "refresh_token": refresh_token,
        }