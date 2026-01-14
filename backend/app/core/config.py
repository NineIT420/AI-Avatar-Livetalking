"""
Application configuration
"""
import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # Session management
    MAX_SESSIONS: int = 1
    
    # MUSETALK configuration
    MODEL: str = "musetalk"
    AVATAR_ID: str = "avator_1"
    BATCH_SIZE: int = 16
    FPS: int = 50
    AUDIO_GAIN: float = 1.0
    
    # Audio processing
    STRIDE_LEFT: int = 10
    STRIDE_MIDDLE: int = 8
    STRIDE_RIGHT: int = 10
    
    # STUN server
    STUN_SERVER: str = "stun:stun.miwifi.com:3478"
    
    # SSL
    SSL_CERT: str = ""
    SSL_KEY: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

