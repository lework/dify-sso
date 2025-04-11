from fastapi import APIRouter
from app.api.endpoints import enterprise, health, sso

router = APIRouter()

router.include_router(sso.router, prefix="/console/api/enterprise/sso") 
router.include_router(enterprise.router)
router.include_router(health.router)
