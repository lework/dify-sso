import logging
import requests
from typing import Dict
from urllib.parse import urlencode,unquote
from datetime import UTC, datetime, timedelta

from app.configs import config
from app.models.account import Account, AccountStatus, TenantAccountJoin,TenantAccountRole
from app.models.engine import db
from app.services.passport import PassportService
from app.services.token import TokenService

logger = logging.getLogger(__name__)

class OIDCService:
    def __init__(self):
        self.client_id = config.OIDC_CLIENT_ID
        self.client_secret = config.OIDC_CLIENT_SECRET
        self.discovery_url = config.OIDC_DISCOVERY_URL
        self.redirect_uri = config.OIDC_REDIRECT_URI
        self.scope = config.OIDC_SCOPE
        self.response_type = config.OIDC_RESPONSE_TYPE
        self.tenant_id = config.TENANT_ID
        self.account_default_role = config.ACCOUNT_DEFAULT_ROLE
        self.passport_service = PassportService()
        self.token_service = TokenService()
        
        # 获取OIDC配置
        self._load_oidc_config()
    
    def _load_oidc_config(self):
        # 加载OIDC配置
        response = requests.get(self.discovery_url)
        if response.status_code == 200:
            oidc_config = response.json()
            self.authorization_endpoint = oidc_config.get('authorization_endpoint')
            self.token_endpoint = oidc_config.get('token_endpoint')
            self.userinfo_endpoint = oidc_config.get('userinfo_endpoint')
            logger.debug("OIDC配置加载成功: %s", oidc_config)
        else:
            logger.error("OIDC配置加载失败: %s", response.text)
            raise Exception("Failed to load OIDC configuration")

    def check_oidc_config(self) -> bool:
        if not self.authorization_endpoint or not self.token_endpoint or not self.userinfo_endpoint:
            return False
        return True

    def get_login_url(self, redirect_uri_params: str = "") -> str:
        # 生成登录URL
        params = {
            'client_id': self.client_id,
            'response_type': self.response_type,
            'scope': self.scope,
            'redirect_uri': self.redirect_uri,
            'state': 'random_state'
        }

        if redirect_uri_params:
            # 拼接查询参数的时候，需要先使用urldecode解码，然后使用urlencode编码
            params['redirect_uri'] = self.redirect_uri + "?" + unquote(redirect_uri_params)

        return f"{self.authorization_endpoint}?{urlencode(params)}"

    def get_token(self, code: str, redirect_uri_params: str = "") -> Dict:
        # 获取访问令牌
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }

        if redirect_uri_params:
            data['redirect_uri'] = self.redirect_uri + "?" + unquote(redirect_uri_params)

        response = requests.post(self.token_endpoint, data=data)
        if response.status_code != 200:
            logger.exception("获取token失败: status_code=%d, response=%s", 
                           response.status_code, response.text)
            raise Exception("Failed to get token")
        return response.json()

    def get_user_info(self, access_token: str) -> Dict:
        # 获取用户信息
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(self.userinfo_endpoint, headers=headers)
        if response.status_code != 200:
            logger.exception("获取用户信息失败: status_code=%d, response=%s", 
                           response.status_code, response.text)
            raise Exception("Failed to get user info")
        return response.json()

    def handle_callback(self, code: str, client_host: str, redirect_uri_params: str = "") -> Dict[str, str]:
        # 处理回调，返回access token和refresh token
        try:
            # 获取访问令牌
            token_response = self.get_token(code, redirect_uri_params)
            access_token = token_response.get('access_token')
            
            # 获取用户信息
            user_info = self.get_user_info(access_token)
            user_name = user_info.get('name')
            user_email = user_info.get('email')
            user_roles = user_info.get('roles', [])
            logger.debug("用户信息: %s", user_info)
            
            # 验证必填字段
            if not user_email:  
                logger.error("用户邮箱信息缺失: %s",  user_info)
                raise Exception("用户邮箱信息缺失")
            
            if not user_name:
                user_name = user_email.split('@')[0]  # 使用邮箱前缀作为默认用户名
            
            # 确定用户角色（按优先级从高到低判断）
            user_role = TenantAccountRole(self.account_default_role) if TenantAccountRole.is_valid_role(self.account_default_role) else TenantAccountRole.NORMAL
            if TenantAccountRole.ADMIN in user_roles:
                user_role = TenantAccountRole.ADMIN
            elif TenantAccountRole.EDITOR in user_roles:
                user_role = TenantAccountRole.EDITOR
            elif TenantAccountRole.NORMAL in user_roles:
                user_role = TenantAccountRole.NORMAL

            # 查找系统用户
            account = Account.get_by_email(user_email)

            # 如果系统用户不存在，则创建系统用户
            if not account:
                logger.info("创建用户: %s, 角色: %s", user_email, user_role)
                account = Account.create(
                    email=user_email,
                    name=user_name,
                    avatar="",
                )
                TenantAccountJoin.create(self.tenant_id, account.id, user_role)
            else:
                # 如果用户已存在，检查是否属于当前租户
                tenant_account_join = TenantAccountJoin.get_by_account(
                    self.tenant_id, account.id
                )
                if not tenant_account_join:
                    logger.info("用户 %s 不属于当前租户，创建关联: 角色 %s", user_email, user_role)
                    tenant_account_join = TenantAccountJoin.create(self.tenant_id, account.id, user_role)
                else:
                    # 更新角色（如果有变化）
                    if tenant_account_join.role != user_role:
                        logger.info("用户角色更新: %s (%s -> %s)", user_email, tenant_account_join.role, user_role)
                        tenant_account_join.role = user_role
                        db.session.add(tenant_account_join)

            # 更新用户登录信息
            account.last_login_at = datetime.now(UTC)
            account.last_login_ip = client_host
            if account.status != AccountStatus.ACTIVE:
                account.status = AccountStatus.ACTIVE
            if account.name != user_name:
                account.name = user_name
            
            db.session.add(account)
            db.session.commit()
            logger.info("用户验证成功: %s, 角色: %s", user_email, user_role)

            # 生成JWT token
            exp_dt = datetime.now(UTC) + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
            exp = int(exp_dt.timestamp())
            account_id = str(account.id)

            if redirect_uri_params:
                payload = {
                    "user_id": account_id,  # 将UUID转换为字符串
                    "session_id": account.email,
                    "auth_type": "internal",
                    "token_source": "webapp_login_token",
                    "exp": exp,
                    "sub": "Web API Passport",
                }

                access_token = self.passport_service.issue(payload)

                return {
                    "access_token": access_token,
                }

            else:
              payload = {
                  "user_id": account_id,  # 将UUID转换为字符串
                  "exp": exp,
                  "iss": config.EDITION,
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
        
        except Exception as e:
            logger.exception("处理OIDC回调时发生错误: %s", str(e))
            raise