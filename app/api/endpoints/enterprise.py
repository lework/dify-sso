from fastapi import APIRouter
from datetime import datetime, timedelta

router = APIRouter()

# 模拟企业信息
MOCK_ENTERPRISE_INFO = {
    "sso_enforced_for_signin": True,
    "sso_enforced_for_signin_protocol": "oidc",
    "sso_enforced_for_web": True,
    "sso_enforced_for_web_protocol": "oidc",
    "enable_web_sso_switch_component": True,
    "enable_email_code_login": True,
    "enable_email_password_login": True,
    "is_allow_register": True,
    "is_allow_create_workspace": False,
    "license": {
        "status": "active",
        "expired_at": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    }
}

# 模拟计费信息
MOCK_BILLING_INFO = {
    "enabled": True,
    "subscription": {
        "plan": "enterprise",
        "interval": "year"
    },
    "members": {
        "size": 1,
        "limit": 100
    },
    "apps": {
        "size": 1,
        "limit": 200
    },
    "vector_space": {
        "size": 1,
        "limit": 500
    },
    "documents_upload_quota": {
        "size": 1,
        "limit": 10000
    },
    "annotation_quota_limit": {
        "size": 1,
        "limit": 10000
    },
    "docs_processing": "top-priority",
    "can_replace_logo": True,
    "model_load_balancing_enabled": True,
    "dataset_operator_enabled": True,
    "knowledge_rate_limit": {
        "limit": 200000,
        "subscription_plan": "enterprise"
    }
}

# 系统功能
SYSTEM_FEATURES = {
    "sso_enforced_for_signin": True,
    "sso_enforced_for_signin_protocol": "oidc",
    "sso_enforced_for_web": True,
    "sso_enforced_for_web_protocol": "oidc",
    "enable_web_sso_switch_component": True,
    "enable_marketplace": True,
    "max_plugin_package_size": 52428800,
    "enable_email_code_login": False,
    "enable_email_password_login": True,
    "enable_social_oauth_login": False,
    "is_allow_register": False,
    "is_allow_create_workspace": False,
    "is_email_setup": True,
    "license": {
        "status": "active",
        "expired_at": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    }
}


@router.get("/info")
async def get_enterprise_info():
    return MOCK_ENTERPRISE_INFO

@router.get("/app-sso-setting")
async def get_app_sso_setting(app_code: str):
    return {
        "enabled": True,
        "protocol": "oidc",
        "app_code": app_code
    } 

# 计费相关接口
@router.get("/subscription/info")
async def get_billing_info():
    return MOCK_BILLING_INFO


# 系统功能
@router.get("/console/api/system-features")
async def get_system_features():
    return SYSTEM_FEATURES
