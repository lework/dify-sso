import math

from flask import request, jsonify

from app.api.router import api, logger
from app.extensions.ext_redis import redis_client
from app.models.account import Account, AccountStatus
from app.models.engine import db
from app.models.model import Site
from app.services.passport import PassportService


@api.get("/info")
def get_enterprise_info():
    logger.info("get_enterprise_info called")
    data = {
        "SSOEnforcedForSignin": True,
        "SSOEnforcedForSigninProtocol": "oidc",
        "SSOEnforcedForWebProtocol": "oidc",
        "EnableEmailCodeLogin": True,
        "EnableEmailPasswordLogin": True,
        "IsAllowRegister": True,
        "IsAllowCreateWorkspace": True,
        "Branding": {
            "applicationTitle": "",
            "loginPageLogo": "",
            "workspaceLogo": "",
            "favicon": "",
        },
        "WebAppAuth": {
            "allowSso": True,
            "allowEmailCodeLogin": True,
            "allowEmailPasswordLogin": True,
        },
        "License": {
            "status": "active",
            "workspaces": {
                "enabled": True,
                "used": 1,
                "limit": 100
            },
            "expiredAt": "2099-12-31T23:59:59Z",
        },
        "PluginInstallationPermission": {
            "pluginInstallationScope": "all",
            "restrictToMarketplaceOnly": True
        }
    }

    return data


@api.get("/sso/app/last-update-time")
@api.get("/sso/workspace/last-update-time")
def get_sso_app_last_update_time():
    return jsonify("2025-01-01T00:00:00+00:00")


@api.post("/webapp/access-mode")
@api.post("/console/api/enterprise/webapp/app/access-mode")
def set_app_access_mode():
    appId = request.json.get("appId", "")
    access_mode = request.json.get("accessMode", "")
    subjects = request.json.get("subjects", [])
    logger.info(f"set_app_access_mode called with appId: {appId}, accessMode: {access_mode}, subjects: {subjects}")

    if appId == "":
        return {"accessMode": "public", "result": False}

    accounts = []
    groups = []
    for subject in subjects:
        subject_id = subject.get("subjectId", "")
        subject_type = subject.get("subjectType", "")
        if subject_type == "account":
            accounts.append(subject_id)
        elif subject_type == "group":
            groups.append(subject_id)

    redis_client.set(f"webapp_access_mode:{appId}", access_mode)
    redis_client.set(f"webapp_access_mode:accounts:{appId}", ",".join(accounts))
    redis_client.set(f"webapp_access_mode:groups:{appId}", ",".join(groups))

    return {"accessMode": access_mode, "result": True}


@api.get("/webapp/access-mode/id")
@api.get("/api/webapp/access-mode")
@api.get("/console/api/enterprise/webapp/app/access-mode")
def get_app_access_mode():
    app_id = request.args.get("appId", "")
    app_code = request.args.get("appCode", "")
    logger.info(f"get_app_access_mode: app_id={app_id}, app_code={app_code}")

    if app_code != "":
        site = db.session.query(Site).filter(Site.code == app_code).first()
        if site:
            app_id = site.app_id
    if app_id == "":
        logger.info(f"app_id is empty, return public")
        return {"accessMode": "public"}
    else:
        access_mode = redis_client.get(f"webapp_access_mode:{app_id}")
        if access_mode:
            logger.info(f"app_id:{app_id}, access_mode: {access_mode.decode()}")
            return {"accessMode": access_mode.decode()}
        else:
            logger.info(f"app_id:{app_id}, access_mode not set, return public")
            return {"accessMode": "public"}


@api.post("/webapp/access-mode/batch/id")
def get_webapp_access_mode_code_batch():
    appIds = request.json.get("appIds", [])
    accessModes = {}
    logger.info(f"get_webapp_access_mode_code_batch: appIds={appIds}")

    for app_id in appIds:
        access_mode = redis_client.get(f"webapp_access_mode:{app_id}")
        if access_mode:
            accessModes[app_id] = access_mode.decode()
        else:
            accessModes[app_id] = "public"

    return {"accessModes": accessModes}


@api.get("/api/webapp/permission")
@api.get("/console/api/enterprise/webapp/permission")
def get_app_permission():
    user_id = "visitor"
    app_id = request.args.get("appId", "")
    app_code = request.args.get("appCode", "")
    logger.info(f"get_app_permission: app_id={app_id}, app_code={app_code}")

    if app_code != "":
        site = db.session.query(Site).filter(Site.code == app_code).first()
        if site:
            app_id = site.app_id
        else:
            logger.info(f"app_code {app_code} not found")
            return {"result": False}

    try:
        auth_header = request.headers.get("Authorization")
        if auth_header is None:
            raise
        if " " not in auth_header:
            raise

        auth_scheme, tk = auth_header.split(None, 1)
        auth_scheme = auth_scheme.lower()
        if auth_scheme != "bearer":
            raise

        decoded = PassportService().verify(tk)
        logger.info(f"app_id {app_id} decoded token: {decoded}")
        user_id = decoded.get("end_user_id", decoded.get("user_id", "visitor"))
    except Exception as e:
        logger.error(f"get_app_permission error: {e}")
        pass

    access_mode = "public"
    access_mode_value = redis_client.get(f"webapp_access_mode:{app_id}")
    if access_mode_value is not None:
        access_mode = access_mode_value.decode()

    if access_mode == "public":
        logger.info(f"app_id {app_id} is public, access granted")
        return {"result": True}

    if access_mode in ["private_all", "sso_verified"] and user_id != "visitor":
        logger.info(f"app_id {app_id} is private_all or sso_verified, user_id {user_id} is not visitor, access granted")
        return {"result": True}
    else:
        accounts_value = redis_client.get(f"webapp_access_mode:accounts:{app_id}")
        if accounts_value:
            accounts = accounts_value.decode().split(",")
            if user_id in accounts:
                logger.info(f"app_id {app_id} has accounts set, user_id {user_id} is in accounts, access granted")
                return {"result": True}
            else:
                logger.info(f"app_id {app_id} has accounts set, user_id {user_id} is not in accounts, access denied")
                return {"result": False}
        else:
            logger.info(f"app_id {app_id} has no accounts set, access denied")
            return {"result": False}


@api.get("/console/api/enterprise/webapp/app/subjects")
def get_app_subjects():
    app_id = request.args.get("appId", "")
    logger.info(f"get_app_subjects: app_id={app_id}")

    if app_id == "":
        return {"groups": [], "members": []}

    accounts_value = redis_client.get(f"webapp_access_mode:accounts:{app_id}")
    if accounts_value:
        accounts = accounts_value.decode().split(",")
        users = db.session.query(Account).filter(Account.status == AccountStatus.ACTIVE, Account.id.in_(accounts)).all()
    else:
        users = []

    members = []
    for user in users:
        members.append({
            "id": str(user.id),
            "name": user.name or "",
            "email": user.email or "",
            "avatar": user.avatar or "",
            "avatarUrl": ""
        })

    return {"groups": [], "members": members}


@api.get("/console/api/enterprise/webapp/app/subject/search")
def search_app_subjects():
    try:
        # 参数验证和获取
        page = max(1, int(request.args.get("pageNumber", 1)))
        page_size = min(100, max(1, int(request.args.get("resultsPerPage", 10))))  # 限制页面大小
        keyword = request.args.get("keyword", "").strip()
        logger.info(f"search_app_subjects: page={page}, page_size={page_size}, keyword={keyword}")

        # 构建基础查询条件
        base_query = db.session.query(Account).filter(Account.status == AccountStatus.ACTIVE)

        # 添加搜索条件 - 支持姓名和邮箱搜索
        if keyword:
            search_filter = db.or_(
                Account.name.ilike(f"%{keyword}%"),
                Account.email.ilike(f"%{keyword}%")
            )
            base_query = base_query.filter(search_filter)

        # 计算总数和分页数据（使用窗口函数优化）
        paginated_query = base_query.order_by(Account.name, Account.id)  # 确保排序稳定性

        # 获取总数
        total_count = base_query.count()

        if total_count == 0:
            return {
                "currPage": page,
                "totalPages": 0,
                "subjects": [],
                "hasMore": False,
            }

        # 分页查询
        offset = (page - 1) * page_size
        users = paginated_query.limit(page_size).offset(offset).all()

        # 构建响应数据
        subjects = [
            {
                "subjectId": str(user.id),
                "subjectType": "account",
                "accountData": {
                    "id": str(user.id),
                    "name": user.name or "",
                    "email": user.email or "",
                    "avatar": user.avatar or "",
                    "avatarUrl": ""
                }
            }
            for user in users
        ]

        # 计算分页信息
        total_pages = math.ceil(total_count / page_size)
        has_more = page < total_pages

        return {
            "currPage": page,
            "totalPages": total_pages,
            "subjects": subjects,
            "hasMore": has_more,
        }

    except ValueError as e:
        # 参数类型错误
        return {
            "error": "Invalid parameter format",
            "message": "pageNumber and resultsPerPage must be valid integers"
        }, 400
    except Exception as e:
        # 其他异常
        return {
            "error": "Internal server error",
            "message": "An error occurred while searching subjects"
        }, 500


@api.get("/webapp/access-mode/code")
def get_webapp_access_mode_code():
    logger.info("get_webapp_access_mode_code called", request.args)
    app_code = request.args.get("app_code", "")
    if app_code == "":
        app_code = request.args.get("appCode", "")

    logger.info(f"get_webapp_access_mode_code: app_code={app_code}")

    if app_code == "":
        logger.info(f"app_code is empty, return public")
        return {"accessMode": "public"}

    site = db.session.query(Site).filter(Site.code == app_code).first()
    if site:
        access_mode_value = redis_client.get(f"webapp_access_mode:{site.app_id}")
        if access_mode_value:
            logger.info(f"app_code:{app_code}, access_mode: {access_mode_value.decode()}")
            return {"accessMode": access_mode_value.decode()}
        else:
            logger.info(f"app_code:{app_code}, access_mode not set, return public")
            return {"accessMode": "public"}
    else:
        logger.info(f"app_code {app_code} not found, return public")
        return {"accessMode": "public"}


@api.get("/webapp/permission")
def get_webapp_permission():
    app_code = request.args.get("appCode", "")
    user_id = request.args.get("userId", "")
    app_id = request.args.get("appId", "")
    logger.info(f"get_webapp_permission: app_code={app_code}, user_id={user_id}")

    if app_code != "":
        site = db.session.query(Site).filter(Site.code == app_code).first()
        if site:
            app_id = site.app_id
        else:
            logger.info(f"app_code {app_code} not found")
            return {"result": False}

    access_mode = "public"
    access_mode_value = redis_client.get(f"webapp_access_mode:{app_id}")
    if access_mode_value is not None:
        access_mode = access_mode_value.decode()

    if access_mode == "public":
        logger.info(f"app_id {app_id} is public, access granted")
        return {"result": True}

    if access_mode in ["private_all", "sso_verified"]:
        logger.info(f"app_id {app_id} is private_all or sso_verified, access granted")
        return {"result": True}
    else:
        accounts_value = redis_client.get(f"webapp_access_mode:accounts:{app_id}")
        if accounts_value:
            accounts = accounts_value.decode().split(",")
            if user_id in accounts:
                logger.info(f"app_id {app_id} has accounts set, user_id {user_id} is in accounts, access granted")
                return {"result": True}
            else:
                logger.info(f"app_id {app_id} has accounts set, user_id {user_id} is not in accounts, access denied")
                return {"result": False}
        else:
            logger.info(f"app_id {app_id} has no accounts set, access denied")
            return {"result": False}


@api.post("/webapp/permission/batch")
def get_webapp_permission_batch():
    appCodes = request.json.get("appCodes", [])
    userId = request.json.get("userId", "")
    permissions = {}
    logger.info(f"get_webapp_permission_batch: appCodes={appCodes}, userId={userId}")

    for app_code in appCodes:
        permissions[app_code] = False
        site = db.session.query(Site).filter(Site.code == app_code).first()
        if site:
            app_id = site.app_id
        else:
            continue

        access_mode = "public"
        access_mode_value = redis_client.get(f"webapp_access_mode:{app_id}")
        if access_mode_value is not None:
            access_mode = access_mode_value.decode()

        if access_mode == "public":
            permissions[app_code] = True
            continue

        if access_mode in ["private_all", "sso_verified"]:
            permissions[app_code] = True
            continue
        else:
            accounts_value = redis_client.get(f"webapp_access_mode:accounts:{app_id}")
            if accounts_value:
                accounts = accounts_value.decode().split(",")
                if userId in accounts:
                    permissions[app_code] = True
                else:
                    permissions[app_code] = False
            else:
                permissions[app_code] = False

    return {"permissions": permissions}


@api.delete("/webapp/clean")
def clean_webapp_access_mode():
    appId = request.args.get("appId", "")
    logger.info(f"clean_webapp_access_mode called with appId: {appId}")

    if appId == "":
        return {"result": False}
    logger.info(f"clean_webapp_access_mode: {appId}")
    redis_client.delete(f"webapp_access_mode:{appId}")
    redis_client.delete(f"webapp_access_mode:groups:{appId}")
    redis_client.delete(f"webapp_access_mode:accounts:{appId}")

    return {"result": True}


# PluginManagerService
@api.post("/check-credential-policy-compliance")
def check_credential_policy_compliance():
    # 示例请求体
    # {'dify_credential_id': '0198eabb-3b2c-793e-a491-3ddf5bfc75a6', 'provider': 'langgenius/tongyi/tongyi', 'credential_type': 0}
    data = request.json
    logger.info(f"check_credential_policy_compliance called with data: {data}")

    return {"result": True}
