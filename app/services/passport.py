import jwt

from app.core.config import settings


class PassportService:
    def __init__(self):
        self.sk = settings.SECRET_KEY

    def issue(self, payload):
        return jwt.encode(payload, self.sk, algorithm="HS256")