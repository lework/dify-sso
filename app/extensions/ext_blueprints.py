from flask import Flask


def init_app(app: Flask):
    # register blueprint routers

    from flask_cors import CORS
    from app.api.router import api


    CORS(
        app,
        origins="*",
        allow_headers="*",
        methods=["GET", "PUT", "POST", "DELETE", "OPTIONS", "PATCH"],
        expose_headers=["X-Version", "X-Env"],
    )

    app.register_blueprint(api)