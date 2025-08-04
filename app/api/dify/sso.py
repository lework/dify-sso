import logging
from flask import request, redirect

from app.configs import config
from app.api.router import api
from app.extensions.ext_oidc import oidc_service

logger = logging.getLogger(__name__)

@api.get("/console/api/enterprise/sso/oidc/login")
def oidc_login():
    is_login = request.args.get("is_login", False)
    login_url = oidc_service.get_login_url()
    if is_login:
        return redirect(login_url)
    else:
        return {"url": login_url}

@api.get("/console/api/enterprise/sso/oidc/callback")
def oidc_callback():
    code = request.args.get("code", "")
    client_host = request.remote_addr
    xff = request.headers.get('X-Forwarded-For')
    if xff:
        xffs = xff.split(',')
        if len(xffs) > 0:
            client_host = xffs[0].strip()

    try:
        tokens = oidc_service.handle_callback(code, client_host)
        return redirect(f"{config.CONSOLE_WEB_URL}/signin?access_token={tokens['access_token']}&refresh_token={tokens['refresh_token']}")
    except Exception as e:
        logger.exception("OIDC回调处理失败: %s", str(e))
        return {"error": str(e)}, 400