from dotenv import load_dotenv
import os
from openai import OpenAI

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", os.urandom(24))
    SESSION_TYPE = "filesystem"
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_FILE_DIR = "/tmp/flask_session"
    SESSION_FILE_THRESHOLD = 100
    SESSION_COOKIE_SAMESITE = "None"
    SESSION_COOKIE_SECURE = True

# OpenAI клієнт
client = OpenAI()
MODEL_ENGINE = "gpt-3.5-turbo"
