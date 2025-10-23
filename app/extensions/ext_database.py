from flask import Flask

from app.models import db


def init_app(app: Flask):
    db.init_app(app)
