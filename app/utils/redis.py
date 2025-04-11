import redis
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

redis_manager = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    decode_responses=True
)

def check_redis_connection() -> bool:
    try:
        redis_manager.ping()
        return True
    except Exception as e:
        logger.exception("Redis连接检查失败: %s", str(e))
        return False 