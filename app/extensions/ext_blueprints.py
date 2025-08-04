from flask import Flask


def init_app(app: Flask):
    # register blueprint routers

    from flask_cors import CORS  # type: ignore

    from app.api.router import api


    CORS(
        api,
        allow_headers=["Content-Type", "Authorization", "X-App-Code"],
        methods=["GET", "PUT", "POST", "DELETE", "OPTIONS", "PATCH"],
    )

    app.register_blueprint(api)