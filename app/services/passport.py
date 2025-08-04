import jwt

from app.configs import config


class PassportService:
    def __init__(self):
        self.sk = config.SECRET_KEY

    # 生成access token
    def issue(self, payload):
        return jwt.encode(payload, self.sk, algorithm="HS256")