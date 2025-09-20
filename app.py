from flask import Flask
from flask_session import Session
from config import Config
from routes import chat_bp, auth_bp, speech_bp, misc_bp

# створюємо Flask-додаток
app = Flask(__name__)
app.config.from_object(Config)

# ініціалізуємо Flask-Session
Session(app)

# реєструємо маршрути
app.register_blueprint(chat_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(speech_bp)
app.register_blueprint(misc_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
