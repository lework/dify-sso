from app.api.router import api, logger


@api.get("/workspace/<string:tenant_id>/info")
def get_workspace_info(tenant_id):
    logger.info(f"get_workspace_info called with tenant_id: {tenant_id}")
    data = {
        "enabled": True,
        "used": 1,
        "limit": 100
    }
    return {"WorkspaceMembers": data}


@api.get("/workspaces/<string:tenant_id>/permission")
def get_workspace_permission(tenant_id):
    logger.info(f"get_workspace_permission called with tenant_id: {tenant_id}")
    return {"permission": {"workspaceId": tenant_id, "allowMemberInvite": True, "allowOwnerTransfer": True}}
