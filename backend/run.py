"""
FastAPI startup script with model initialization
"""
import argparse
import json
import torch.multiprocessing as mp
from app.main import app
from app.core.config import settings
from app.services.session_manager import session_manager
import logging

logger = logging.getLogger(__name__)


def create_opt_from_args():
    """Create opt object from command line arguments"""
    parser = argparse.ArgumentParser()
    
    # Audio FPS
    parser.add_argument('--fps', type=int, default=50, help="audio fps, must be 50")
    # Sliding window left-middle-right length (unit: 20ms)
    parser.add_argument('-l', type=int, default=10)
    parser.add_argument('-m', type=int, default=8)
    parser.add_argument('-r', type=int, default=10)
    
    parser.add_argument('--W', type=int, default=450, help="GUI width")
    parser.add_argument('--H', type=int, default=450, help="GUI height")
    
    # MUSETALK opt
    parser.add_argument('--avatar_id', type=str, default='avator_1', help="define which avatar in data/avatars")
    parser.add_argument('--batch_size', type=int, default=16, help="infer batch")
    parser.add_argument('--audio_gain', type=float, default=1.0, help="Audio gain multiplier")
    
    parser.add_argument('--customvideo_config', type=str, default='', help="custom action json")
    parser.add_argument('--tts', type=str, default='edgetts', help="tts service type")
    parser.add_argument('--REF_FILE', type=str, default="zh-CN-YunxiaNeural")
    parser.add_argument('--REF_TEXT', type=str, default=None)
    parser.add_argument('--TTS_SERVER', type=str, default='http://127.0.0.1:9880')
    
    parser.add_argument('--model', type=str, default='musetalk')
    parser.add_argument('--transport', type=str, default='webrtc')
    parser.add_argument('--push_url', type=str, default='http://localhost:1985/rtc/v1/whip/?app=live&stream=livestream')
    parser.add_argument('--max_session', type=int, default=1)
    parser.add_argument('--listenport', type=int, default=8000)
    parser.add_argument('--ssl_cert', type=str, default='')
    parser.add_argument('--ssl_key', type=str, default='')
    
    opt = parser.parse_args()
    
    # Load custom video config if provided
    opt.customopt = []
    if opt.customvideo_config != '':
        with open(opt.customvideo_config, 'r') as file:
            opt.customopt = json.load(file)
    
    return opt


if __name__ == "__main__":
    mp.set_start_method('spawn')
    
    # Parse arguments
    opt = create_opt_from_args()
    
    # Update settings from opt
    settings.MODEL = opt.model
    settings.AVATAR_ID = opt.avatar_id
    settings.BATCH_SIZE = opt.batch_size
    settings.FPS = opt.fps
    settings.AUDIO_GAIN = opt.audio_gain
    settings.MAX_SESSIONS = opt.max_session
    settings.PORT = opt.listenport
    settings.SSL_CERT = opt.ssl_cert
    settings.SSL_KEY = opt.ssl_key
    
    # Initialize model
    logger.info("Initializing model...")
    session_manager.initialize_model(opt)
    logger.info("Model initialized successfully")
    
    # Run server
    import uvicorn
    
    ssl_keyfile = settings.SSL_KEY if settings.SSL_KEY else None
    ssl_certfile = settings.SSL_CERT if settings.SSL_CERT else None
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile,
    )

