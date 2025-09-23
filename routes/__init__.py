from .chat_routes import chat_bp
from .auth_routes import auth_bp
from .speech_routes import speech_bp
from .misc_routes import misc_bp

__all__ = ["chat_bp", "auth_bp", "speech_bp", "misc_bp"]
