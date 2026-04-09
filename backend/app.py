import os

from flask import Flask
from flask_cors import CORS

from config import Config
from db import init_db
from routes.sentiment import sentiment_bp
from routes.trading import trading_bp
from routes.chatbot import chatbot_bp
from routes.health import health_bp
from routes.auth import auth_bp

app = Flask(__name__)
app.config.from_object(Config)
init_db()
CORS(app, origins=[r"http://localhost:\d+"], supports_credentials=True)

app.register_blueprint(health_bp, url_prefix="/api")
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(sentiment_bp, url_prefix="/api/sentiment")
app.register_blueprint(trading_bp, url_prefix="/api/trading")
app.register_blueprint(chatbot_bp, url_prefix="/api/chatbot")


@app.route("/")
def index():
    return {"name": "STO API", "description": "Social Trend Observant", "version": "0.1.0"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, port=port)
