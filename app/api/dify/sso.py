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
    redirect_url = request.args.get("redirect_url", "")
    app_code = request.args.get("app_code", "")

    client_host = request.remote_addr
    xff = request.headers.get('X-Forwarded-For')
    if xff:
        xffs = xff.split(',')
        if len(xffs) > 0:
            client_host = xffs[0].strip()

    try:
        if app_code and redirect_url:
            tokens = oidc_service.handle_callback(code, client_host, f"app_code={app_code}&redirect_url={redirect_url}")
            return redirect(f"{config.CONSOLE_WEB_URL}/webapp-signin?web_sso_token={tokens['access_token']}&redirect_url={redirect_url}")
        else:
            tokens = oidc_service.handle_callback(code, client_host)
            return redirect(f"{config.CONSOLE_WEB_URL}/signin?access_token={tokens['access_token']}&refresh_token={tokens['refresh_token']}&redirect_url={redirect_url}")
    except Exception as e:
        logger.exception("OIDC回调处理失败: %s", str(e))
        return {"error": str(e)}, 400

@api.get("/api/enterprise/sso/members/oidc/login")
def oidc_login_callback():
    app_code = request.args.get("app_code", "")
    redirect_url = request.args.get("redirect_url", "")
    login_url = oidc_service.get_login_url(f"app_code={app_code}&redirect_url={redirect_url}")
    return redirect(login_url)