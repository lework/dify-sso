import logging

from flask import Blueprint, jsonify, request
from sqlalchemy import text

from app.extensions.ext_redis import redis_client
from app.models import db

logger = logging.getLogger(__name__)

api = Blueprint("api", __name__, url_prefix="/")


@api.route("/")
def index():
    return "Hello, World!"


@api.get("/health")
def health_check():
    detail = request.args.get("detail", False)
    if detail:
        try:
            db.session.execute(text("SELECT 1")).fetchone()
            database_status = True
        except Exception as e:
            logger.exception("Database connection failed: %s", str(e))
            database_status = False

        try:
            redis_client.ping()
            redis_status = True
        except Exception as e:
            logger.exception("Redis connection failed: %s", str(e))
            redis_status = False

        health_status = {
            "status": "healthy" if database_status and redis_status else "unhealthy",
            "database": database_status,
            "redis": redis_status
        }
    else:
        health_status = {
            "status": "healthy",
        }

    return health_status


# 处理错误
@api.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Not found"}), 404


@api.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


# 导入endpoints
from .dify import sso, enterprise, webapp  # noqa: F401
