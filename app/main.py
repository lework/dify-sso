import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.router import router
from app.db.session import check_database_connection, engine
from app.utils.redis import check_redis_connection, redis_manager
from app.models.account import Base
from app.api.endpoints.sso import oidc_service

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建数据库表
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("Starting application")
    # 检查数据库连接
    if not check_database_connection():
        logger.error("Failed to connect to PostgreSQL database")
        raise Exception("Database connection failed")
    logger.info("Database connection successful")

    # 检查Redis连接
    if not check_redis_connection():
        logger.error("Failed to connect to Redis")
        raise Exception("Redis connection failed")
    logger.info("Redis connection successful")

    # 检查OIDC配置
    if not  oidc_service.check_oidc_config():
        logger.error("OIDC configuration is incomplete")
        raise Exception("OIDC configuration is incomplete")
    logger.info("OIDC configuration is complete")

    yield
    
    # 关闭时执行
    redis_manager.close()
    logger.info("Redis connection pool closed")
    
    # 关闭数据库连接池
    engine.dispose()
    logger.info("PostgreSQL connection pool closed")

app = FastAPI(lifespan=lifespan)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 