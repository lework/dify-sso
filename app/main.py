from app.app import create_app
from app.configs import config

app = create_app("dify-sso-server")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=config.DEBUG)
