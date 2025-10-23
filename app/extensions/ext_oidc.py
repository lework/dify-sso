from flask import Flask

from app.services.oidc import OIDCService

oidc_service = OIDCService()


def init_app(app: Flask):
    app.extensions["oidc"] = oidc_service
