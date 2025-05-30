import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Server settings
    PORT = int(os.getenv("PORT", 8000))
    HOST = os.getenv("HOST", "0.0.0.0")
    
    # CORS settings
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # File storage settings
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(os.path.dirname(os.path.dirname(__file__)), "music"))
    
    # Soundslice settings
    SOUNDSLICE_APP_ID = os.getenv("SOUNDSLICE_APP_ID")
    SOUNDSLICE_PASSWORD = os.getenv("SOUNDSLICE_PASSWORD")
    
    # Redis settings
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

    @classmethod
    def initialize(cls):
        """Initialize configuration and create necessary directories"""
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True) 