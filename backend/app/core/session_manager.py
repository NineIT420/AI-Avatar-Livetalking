import asyncio
from typing import Dict
from concurrent.futures import ThreadPoolExecutor

from config.settings import settings
from ..utils.logger import logger


class SessionManager:

    def __init__(self):
        self.nerfreals: Dict[int, object] = {}
        self.executor = ThreadPoolExecutor(max_workers=4)

    def create_session(self, sessionid: int):
        self.nerfreals[sessionid] = None

    def session_exists(self, sessionid: int) -> bool:
        return sessionid in self.nerfreals and self.nerfreals[sessionid] is not None

    def cleanup_session(self, sessionid: int):
        """Clean up a session."""
        if sessionid in self.nerfreals:
            del self.nerfreals[sessionid]

    def build_nerfreal(self, sessionid: int):
        from ..services import model_service

        settings.sessionid = sessionid
        if settings.model == 'wav2lip':
            raise NotImplementedError("Wav2Lip model not yet implemented")
        elif settings.model == 'musetalk':
            from ..models.musereal import MuseReal
            nerfreal = MuseReal(settings, model_service.model, model_service.avatar)
        elif settings.model == 'ultralight':
            raise NotImplementedError("UltraLight model not yet implemented")
        else:
            raise ValueError(f"Unknown model type: {settings.model}")
        return nerfreal

    def put_text(self, sessionid: int, text: str):
        if self.session_exists(sessionid):
            self.nerfreals[sessionid].put_msg_txt(text)

    def put_audio(self, sessionid: int, audio_data: bytes):
        if self.session_exists(sessionid):
            self.nerfreals[sessionid].put_audio_file(audio_data)

    def handle_chat(self, sessionid: int, text: str):
        if self.session_exists(sessionid):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                from ..services.llm_service import llm_response
                result = loop.run_until_complete(llm_response(text, self.nerfreals[sessionid]))
                self.nerfreals[sessionid].put_msg_txt(result)
            finally:
                loop.close()

    def interrupt_session(self, sessionid: int):
        if self.session_exists(sessionid):
            self.nerfreals[sessionid].flush_talk()

    def set_audio_type(self, sessionid: int, audiotype: str, reinit: bool):
        if self.session_exists(sessionid):
            self.nerfreals[sessionid].set_custom_state(audiotype, reinit)

    def start_recording(self, sessionid: int):
        if self.session_exists(sessionid):
            self.nerfreals[sessionid].start_recording()

    def stop_recording(self, sessionid: int):
        if self.session_exists(sessionid):
            self.nerfreals[sessionid].stop_recording()

    def is_speaking(self, sessionid: int) -> bool:
        if self.session_exists(sessionid):
            return self.nerfreals[sessionid].is_speaking()
        return False

session_manager = SessionManager()
