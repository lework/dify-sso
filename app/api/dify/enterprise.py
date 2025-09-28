from flask import request
from datetime import datetime, timedelta

from gunicorn.glogging import loggers

from app.api.router import api

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
    "enable_marketplace": True,
    "max_plugin_package_size": 52428800,
    "enable_email_code_login": False,
    "enable_email_password_login": False,
    "enable_social_oauth_login": False,
    "is_allow_register": False,
    "is_allow_create_workspace": False,
    "is_email_setup": True,
    "license": {
        "status": "active",
        "expired_at": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        "workspaces": {
            "enabled": True,
            "size": 0,
            "limit": 0
        }
    },
    "branding": {
        "enabled": False,
        "application_title": "",
        "login_page_logo": "",
        "workspace_logo": "",
        "favicon": ""
    },
    "webapp_auth": {
        "enabled": True,
        "allow_sso": True,
        "sso_config": {
            "protocol": "oidc",
        },
        "allow_email_code_login": False,
        "allow_email_password_login": False
    },
    "plugin_installation_permission": {
        "plugin_installation_scope": "all",
        "restrict_to_marketplace_only": True
    },
    "enable_change_email": True
}

FEATURES = {
    "billing": {
        "enabled": False,
        "subscription": {
            "plan": "enterprise",
            "interval": "year"
        }
    },
    "education": {
        "enabled": False,
        "activated": False
    },
    "members": {
        "size": 0,
        "limit": 0
    },
    "apps": {
        "size": 0,
        "limit": 0
    },
    "vector_space": {
        "size": 0,
        "limit": 0
    },
    "knowledge_rate_limit": {
        "limit": 200000,
        "subscription_plan": "enterprise"
    },
    "annotation_quota_limit": {
        "size": 0,
        "limit": 0
    },
    "documents_upload_quota": {
        "size": 0,
        "limit": 0
    },
    "docs_processing": "top-priority",
    "can_replace_logo": True,
    "model_load_balancing_enabled": True,
    "dataset_operator_enabled": True,
    "webapp_copyright_enabled": True,
    "workspace_members": {
        "enabled": True,
        "size": 1,
        "limit": 100
    },
    "is_allow_transfer_workspace": True
}


# @api.get("/info")
# def get_enterprise_info():
#     return MOCK_ENTERPRISE_INFO

@api.get("/app-sso-setting")
def get_app_sso_setting():
    app_code = request.args.get("app_code", "")

    return {
        "enabled": True,
        "protocol": "oidc",
        "app_code": app_code
    } 

# 计费相关接口
@api.get("/subscription/info")
def get_billing_info():
    return MOCK_BILLING_INFO


# 系统功能
@api.get("/console/api/system-features")
def get_system_features():
    return SYSTEM_FEATURES

@api.get("/console/api/features")
def get_features():
    return FEATURES