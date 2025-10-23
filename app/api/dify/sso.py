import logging

from flask import request, redirect

from app.api.router import api
from app.configs import config
from app.extensions.ext_oidc import oidc_service
from app.libs.helper import extract_remote_ip
from app.services.account import AccountService
from app.services.token import TokenService

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

    remote_ip = extract_remote_ip(request)

    try:
        if app_code and redirect_url:
            tokens = oidc_service.handle_callback(code, remote_ip, f"app_code={app_code}&redirect_url={redirect_url}",
                                                  app_code)
            return redirect(
                f"{config.CONSOLE_WEB_URL}/webapp-signin?web_sso_token={tokens['access_token']}&redirect_url={redirect_url}")
        else:
            account = oidc_service.bind_account(code, remote_ip)
            token_pair = AccountService.login(account, remote_ip)

            response = redirect(f"{config.CONSOLE_WEB_URL}")

            TokenService.set_access_token_to_cookie(response, token_pair.access_token)
            TokenService.set_refresh_token_to_cookie(response, token_pair.refresh_token)
            TokenService.set_csrf_token_to_cookie(response, token_pair.csrf_token)

            return response

    except Exception as e:
        logger.exception("OIDC回调处理失败: %s", str(e))
        return {"error": str(e)}, 400


@api.get("/api/enterprise/sso/oidc/login")
@api.get("/api/enterprise/sso/members/oidc/login")
def oidc_login_callback():
    app_code = request.args.get("app_code", "")
    redirect_url = request.args.get("redirect_url", "")
    login_url = oidc_service.get_login_url(f"app_code={app_code}&redirect_url={redirect_url}")
    return {"url": login_url}
