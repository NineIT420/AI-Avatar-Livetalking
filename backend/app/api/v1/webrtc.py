"""
WebRTC endpoints
"""
import logging
from fastapi import APIRouter, HTTPException
from aiortc import RTCSessionDescription

from fastapi import Depends
from app.schemas.webrtc import OfferRequest, OfferResponse
from app.core.config import settings
from app.core.dependencies import get_session_manager, get_webrtc_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/offer", response_model=OfferResponse)
async def handle_offer(
    request: OfferRequest,
    session_mgr = Depends(get_session_manager),
    webrtc_mgr = Depends(get_webrtc_manager)
):
    """
    Handle WebRTC offer and return answer with session ID
    """
    try:
        # Check max sessions
        if len(session_mgr.sessions) >= settings.MAX_SESSIONS:
            raise HTTPException(
                status_code=429,
                detail={"code": -1, "msg": "Maximum sessions reached"}
            )
        
        # Generate session ID
        sessionid = session_mgr.generate_session_id()
        
        # Create offer object
        offer = RTCSessionDescription(
            sdp=request.sdp,
            type=request.type
        )
        
        # Handle offer and get answer
        answer = await webrtc_mgr.handle_offer(offer, sessionid, session_mgr)
        
        return OfferResponse(
            sdp=answer.sdp,
            type=answer.type,
            sessionid=sessionid
        )
        
    except Exception as e:
        logger.exception(f"Error handling WebRTC offer: {e}")
        raise HTTPException(
            status_code=500,
            detail={"code": -1, "msg": str(e)}
        )

