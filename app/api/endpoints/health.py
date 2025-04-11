from fastapi import APIRouter, HTTPException
from app.utils.redis import check_redis_connection
from app.db.session import check_database_connection

router = APIRouter()

@router.get("/health")
async def health_check(detail: bool = False):
    if detail:
        health_status = {
            "status": "healthy",
            "redis": check_redis_connection(),
            "database": check_database_connection()
        }
        if not health_status["redis"] or not health_status["database"]:
          health_status["status"] = "unhealthy"
          raise HTTPException(
              status_code=503, 
              detail={
                  "redis": "Redis connection failed" if not health_status["redis"] else "OK",
                  "database": "Database connection failed" if not health_status["database"] else "OK"
              }
          )
    else:
        health_status = {
            "status": "healthy",
        }
    
    return health_status 