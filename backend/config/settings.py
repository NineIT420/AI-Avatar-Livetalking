import os
import json
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        self.fps: int = int(os.getenv('LIVETALKING_FPS', '25'))
        self.l: int = int(os.getenv('LIVETALKING_L', '50'))
        self.m: int = int(os.getenv('LIVETALKING_M', '50'))
        self.r: int = int(os.getenv('LIVETALKING_R', '50'))
        self.W: int = int(os.getenv('LIVETALKING_W', '256'))
        self.H: int = int(os.getenv('LIVETALKING_H', '256'))

        self.avatar_id: str = os.getenv('LIVETALKING_AVATAR_ID', 'avator')
        self.batch_size: int = int(os.getenv('LIVETALKING_BATCH_SIZE', '8'))
        self.audio_gain: float = float(os.getenv('LIVETALKING_AUDIO_GAIN', '1.0'))
        self.customvideo_config: str = os.getenv('LIVETALKING_CUSTOMVIDEO_CONFIG', '')
        self.tts: str = os.getenv('LIVETALKING_TTS', 'edge')
        self.model: str = os.getenv('LIVETALKING_MODEL', 'musetalk')

        self.REF_FILE: str = os.getenv('LIVETALKING_REF_FILE', '')
        self.REF_TEXT: str = os.getenv('LIVETALKING_REF_TEXT', '')

        self.TTS_SERVER: str = os.getenv('LIVETALKING_TTS_SERVER', '')
        self.transport: str = os.getenv('LIVETALKING_TRANSPORT', 'webrtc')
        self.push_url: str = os.getenv('LIVETALKING_PUSH_URL', '')
        self.max_session: int = int(os.getenv('LIVETALKING_MAX_SESSION', '10'))
        self.listenport: int = int(os.getenv('LIVETALKING_LISTENPORT', '8000'))

        self.ssl_cert: str = os.getenv('LIVETALKING_SSL_CERT', '')
        self.ssl_key: str = os.getenv('LIVETALKING_SSL_KEY', '')

        self.video: str = os.getenv('LIVETALKING_VIDEO', '')

        self.customopt: list = []
        if self.customvideo_config and os.path.exists(self.customvideo_config):
            with open(self.customvideo_config, 'r') as file:
                self.customopt = json.load(file)

    def to_dict(self) -> Dict[str, Any]:
        return vars(self)

    def __repr__(self) -> str:
        return f"Settings({self.to_dict()})"

settings = Settings()
