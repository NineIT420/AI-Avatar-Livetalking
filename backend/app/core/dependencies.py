"""
FastAPI dependencies
"""
from app.main import session_manager, webrtc_manager


def get_session_manager():
    """Get session manager instance"""
    if session_manager is None:
        raise RuntimeError("Session manager not initialized")
    return session_manager


def get_webrtc_manager():
    """Get WebRTC manager instance"""
    if webrtc_manager is None:
        raise RuntimeError("WebRTC manager not initialized")
    return webrtc_manager

