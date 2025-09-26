import math
from flask import request

from app.api.router import api, logger
from app.services.passport import PassportService
from app.models.account import Account,AccountStatus
from app.models.engine import db
from app.extensions.ext_redis import redis_client
from app.models.model import Site


# @api.get("/info")
# def get_enterprise_info():
#     data = {
#         "SSOEnforcedForSignin": True,
#         "SSOEnforcedForSigninProtocol": "oidc",
#         "EnableEmailCodeLogin": True,
#         "EnableEmailPasswordLogin": True,
#         "IsAllowRegister": True,
#         "IsAllowCreateWorkspace": True,
#         "Branding": {
#             "applicationTitle": "",
#             "loginPageLogo": "",
#             "workspaceLogo": "",
#             "favicon": "",
#         },
#         "WebAppAuth": {
#             "allowSso": True,
#             "allowEmailCodeLogin": True,
#             "allowEmailPasswordLogin": True,
#             "SSOEnforcedForWebProtocol": "oidc",
#         },
#         "License": {
#             "status": "active",
#             "workspaces": {
#                 "enabled": True,
#                 "used": 1,
#                 "limit": 100
#             },
#             "expiredAt": "2099-12-31T23:59:59Z",
#         },
#         "PluginInstallationPermission": {
#             "pluginInstallationScope": "all",
#             "restrictToMarketplaceOnly": False
#         }
#     }
#
#     return data

@api.get("/workspace/<string:tenant_id>/info")
def get_workspace_info(tenant_id):
    data = {
        "enabled": True,
        "used": 1,
        "limit": 100
    }
    return {"WorkspaceMembers": data}

@api.get("/sso/app/last-update-time")
@api.get("/sso/workspace/last-update-time")
def get_sso_app_last_update_time():
    return "2025-01-01T00:00:00Z"


@api.post("/webapp/access-mode")
@api.post("/console/api/enterprise/webapp/app/access-mode")
def set_app_access_mode():

    appId = request.json.get("appId", "")
    access_mode = request.json.get("accessMode", "")
    subjects = request.json.get("subjects", [])

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
    if app_code != "":
        site = db.session.query(Site).filter(Site.code == app_code).first()
        logger.info(f"site: {site}")
        if site:
            app_id = site.app_id
    if app_id == "":
        return {"accessMode": "public"}
    else:
        access_mode = redis_client.get(f"webapp_access_mode:{app_id}")
        if access_mode:
            logger.info(f"access_mode: {access_mode.decode()}")
            return {"accessMode": access_mode.decode()}
        else:
            return {"accessMode": "public"}

@api.post("/webapp/access-mode/batch/id")
def get_webapp_access_mode_code_batch():
    appIds = request.json.get("appIds", [])
    accessModes = {}
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

    if app_code != "":
        site = db.session.query(Site).filter(Site.code == app_code).first()
        logger.info(f"site: {site}")
        if site:
            app_id = site.app_id
        else:
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
        user_id = decoded.get("end_user_id", decoded.get("user_id", "visitor"))
    except Exception as e:
        logger.error(f"get_app_permission error: {e}")
        pass

    access_mode = "public"
    access_mode_value = redis_client.get(f"webapp_access_mode:{app_id}")
    if access_mode_value is not None:
        access_mode = access_mode_value.decode()

    if access_mode == "public":
        return {"result": True}

    if access_mode in ["private_all", "sso_verified"] and user_id != "visitor":
        return {"result": True}
    else:
        accounts_value = redis_client.get(f"webapp_access_mode:accounts:{app_id}")
        if accounts_value:
            accounts = accounts_value.decode().split(",")
            if user_id in accounts:
                return {"result": True}
            else:
                return {"result": False}
        else:
            return {"result": False}

@api.get("/console/api/enterprise/webapp/app/subjects")
def get_app_subjects():
    app_id = request.args.get("appId", "")
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
    app_code = request.args.get("app_code", "")
    if app_code == "":
        return {"accessMode": "public"}

    site = db.session.query(Site).filter(Site.code == app_code).first()
    if site:
         access_mode_value = redis_client.get(f"webapp_access_mode:{site.app_id}")
         if access_mode_value:
            return {"accessMode": access_mode_value.decode()}
         else:
            return {"accessMode": "public"}
    else:
       return {"accessMode": "public"}

@api.get("/webapp/permission")
def get_webapp_permission():
    app_code = request.args.get("appCode", "")
    user_id = request.args.get("userId", "")

    if app_code != "":
        site = db.session.query(Site).filter(Site.code == app_code).first()
        if site:
            app_id = site.app_id
        else:
            return {"result": False}

    access_mode = "public"
    access_mode_value = redis_client.get(f"webapp_access_mode:{app_id}")
    if access_mode_value is not None:
        access_mode = access_mode_value.decode()

    if access_mode == "public":
        return {"result": True}

    if access_mode in ["private_all", "sso_verified"]:
        return {"result": True}
    else:
        accounts_value = redis_client.get(f"webapp_access_mode:accounts:{app_id}")
        if accounts_value:
            accounts = accounts_value.decode().split(",")
            if user_id in accounts:
                return {"result": True}
            else:
                return {"result": False}
        else:
            return {"result": False}

@api.post("/webapp/permission/batch")
def get_webapp_permission_batch():
    appCodes = request.json.get("appCodes", [])
    userId = request.json.get("userId", "")
    permissions = {}

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

@api.delete("/webapp/clean")
def clean_webapp_access_mode():
    appId = request.args.get("appId", "")
    if appId == "":
        return {"result": False}
    logger.info(f"clean_webapp_access_mode: {appId}")
    redis_client.delete(f"webapp_access_mode:{appId}")
    redis_client.delete(f"webapp_access_mode:groups:{appId}")
    redis_client.delete(f"webapp_access_mode:accounts:{appId}")
    return {"result": True}