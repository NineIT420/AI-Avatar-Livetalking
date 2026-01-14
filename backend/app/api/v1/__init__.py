"""
API v1 router
"""
from fastapi import APIRouter

from app.api.v1 import webrtc, recording, audio

router = APIRouter()

router.include_router(webrtc.router, prefix="/webrtc", tags=["webrtc"])
router.include_router(recording.router, prefix="/recording", tags=["recording"])
router.include_router(audio.router, prefix="/audio", tags=["audio"])
