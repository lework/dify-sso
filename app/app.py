import logging
import time

from flask import Flask

from app.configs import config
from app.extensions.ext_oidc import oidc_service


def create_app(name: str) -> Flask:
    start_time = time.perf_counter()
    app = Flask(name)
    app.config.from_mapping(config.model_dump())
    app.uptime = time.time()

    initialize_extensions(app)

    end_time = time.perf_counter()
    if config.DEBUG:
        logging.info("Finished create_app (%s ms)", round((end_time - start_time) * 1000, 2))

    # 启动前检查
    check_app_config(app)

    return app


def check_app_config(app: Flask):
    if not oidc_service.check_oidc_config():
        raise Exception("OIDC配置不完整，请检查配置文件!")


def initialize_extensions(app: Flask):
    from app.extensions import ext_database, ext_redis, ext_logging, ext_timezone, ext_blueprints, ext_oidc

    extensions = [ext_database, ext_redis, ext_logging, ext_timezone, ext_blueprints, ext_oidc]

    for ext in extensions:
        short_name = ext.__name__.split(".")[-1]
        start_time = time.perf_counter()
        ext.init_app(app)
        end_time = time.perf_counter()
        if config.DEBUG:
            logging.info("Loaded %s (%s ms)", short_name, round((end_time - start_time) * 1000, 2))
