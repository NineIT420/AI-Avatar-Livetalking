"""
Recording endpoints
"""
import logging
from fastapi import APIRouter, HTTPException

from fastapi import Depends
from app.schemas.recording import RecordRequest, IsSpeakingRequest, IsSpeakingResponse
from app.schemas.webrtc import BaseResponse
from app.core.dependencies import get_session_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/start-stop", response_model=BaseResponse)
async def handle_recording(
    request: RecordRequest,
    session_mgr = Depends(get_session_manager)
):
    """
    Start or stop recording for a session
    """
    try:
        sessionid = request.sessionid
        nerfreal = session_mgr.get_session(sessionid)
        
        if nerfreal is None:
            raise HTTPException(
                status_code=404,
                detail={"code": -1, "msg": f"Session {sessionid} not found"}
            )
        
        if request.type == "start_record":
            nerfreal.start_recording()
            logger.info(f"Started recording for session {sessionid}")
        elif request.type == "end_record":
            nerfreal.stop_recording()
            logger.info(f"Stopped recording for session {sessionid}")
        
        return BaseResponse(code=0, msg="ok")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error handling recording request: {e}")
        raise HTTPException(
            status_code=500,
            detail={"code": -1, "msg": str(e)}
        )


@router.post("/is-speaking", response_model=IsSpeakingResponse)
async def is_speaking(
    request: IsSpeakingRequest,
    session_mgr = Depends(get_session_manager)
):
    """
    Check if a session is currently speaking
    """
    try:
        sessionid = request.sessionid
        nerfreal = session_mgr.get_session(sessionid)
        
        if nerfreal is None:
            raise HTTPException(
                status_code=404,
                detail={"code": -1, "msg": f"Session {sessionid} not found"}
            )
        
        is_speaking_status = nerfreal.is_speaking()
        
        return IsSpeakingResponse(
            code=0,
            data=is_speaking_status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error checking speaking status: {e}")
        raise HTTPException(
            status_code=500,
            detail={"code": -1, "msg": str(e)}
        )

