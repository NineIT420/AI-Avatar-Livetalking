"""
Session management service
"""
import asyncio
import logging
import random
from typing import Dict, Optional
import torch.multiprocessing as mp

from app.core.config import settings
from basereal import BaseReal

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages LiveTalking sessions"""
    
    def __init__(self):
        self.sessions: Dict[int, Optional[BaseReal]] = {}
        self.model = None
        self.avatar = None
        self.opt = None
        
    def initialize_model(self, opt):
        """Initialize model and avatar (called once)"""
        if self.model is not None:
            return  # Already initialized
            
        self.opt = opt
        
        if opt.model == 'musetalk':
            from musereal import MuseReal, load_model, load_avatar, warm_up
            logger.info(f"Loading MUSETALK model with config: {opt}")
            self.model = load_model()
            self.avatar = load_avatar(opt.avatar_id)
            warm_up(opt.batch_size, self.model)
        elif opt.model == 'wav2lip':
            from lipreal import LipReal, load_model, load_avatar, warm_up
            logger.info(f"Loading Wav2Lip model with config: {opt}")
            self.model = load_model("./models/wav2lip.pth")
            self.avatar = load_avatar(opt.avatar_id)
            warm_up(opt.batch_size, self.model, 256)
        elif opt.model == 'ultralight':
            from lightreal import LightReal, load_model, load_avatar, warm_up
            logger.info(f"Loading Ultralight model with config: {opt}")
            self.model = load_model(opt)
            self.avatar = load_avatar(opt.avatar_id)
            warm_up(opt.batch_size, self.avatar, 160)
    
    def _build_nerfreal(self, sessionid: int) -> BaseReal:
        """Build a new session instance"""
        if self.opt is None:
            raise RuntimeError("Model not initialized. Call initialize_model first.")
            
        self.opt.sessionid = sessionid
        
        if self.opt.model == 'wav2lip':
            from lipreal import LipReal
            return LipReal(self.opt, self.model, self.avatar)
        elif self.opt.model == 'musetalk':
            from musereal import MuseReal
            return MuseReal(self.opt, self.model, self.avatar)
        elif self.opt.model == 'ultralight':
            from lightreal import LightReal
            return LightReal(self.opt, self.model, self.avatar)
        else:
            raise ValueError(f"Unknown model: {self.opt.model}")
    
    def create_session(self, sessionid: int) -> BaseReal:
        """Create a new session"""
        if sessionid in self.sessions and self.sessions[sessionid] is not None:
            logger.warning(f"Session {sessionid} already exists")
            return self.sessions[sessionid]
        
        self.sessions[sessionid] = None
        logger.info(f"Creating session {sessionid}, total sessions: {len(self.sessions)}")
        
        # Build session in executor to avoid blocking
        nerfreal = self._build_nerfreal(sessionid)
        self.sessions[sessionid] = nerfreal
        
        return nerfreal
    
    async def create_session_async(self, sessionid: int) -> BaseReal:
        """Create a new session asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.create_session, sessionid)
    
    def get_session(self, sessionid: int) -> Optional[BaseReal]:
        """Get session by ID"""
        return self.sessions.get(sessionid)
    
    def delete_session(self, sessionid: int):
        """Delete a session"""
        if sessionid in self.sessions:
            del self.sessions[sessionid]
            logger.info(f"Deleted session {sessionid}, remaining sessions: {len(self.sessions)}")
    
    def cleanup_all(self):
        """Cleanup all sessions"""
        logger.info(f"Cleaning up {len(self.sessions)} sessions")
        self.sessions.clear()
    
    def generate_session_id(self) -> int:
        """Generate a random 6-digit session ID"""
        min_id = 10 ** 5
        max_id = 10 ** 6
        sessionid = random.randint(min_id, max_id - 1)
        
        # Ensure unique
        while sessionid in self.sessions:
            sessionid = random.randint(min_id, max_id - 1)
        
        return sessionid

