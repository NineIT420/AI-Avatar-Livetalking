"""
Audio endpoints
"""
import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from fastapi import Depends
from app.schemas.webrtc import BaseResponse
from app.core.dependencies import get_session_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload", response_model=BaseResponse)
async def upload_audio(
    file: UploadFile = File(...),
    sessionid: int = Form(...),
    session_mgr = Depends(get_session_manager)
):
    """
    Upload audio file for a session
    """
    try:
        nerfreal = session_mgr.get_session(sessionid)
        
        if nerfreal is None:
            raise HTTPException(
                status_code=404,
                detail={"code": -1, "msg": f"Session {sessionid} not found"}
            )
        
        # Read file bytes
        filebytes = await file.read()
        
        # Process audio file
        nerfreal.put_audio_file(filebytes)
        
        logger.info(f"Uploaded audio file for session {sessionid}, size: {len(filebytes)} bytes")
        
        return BaseResponse(code=0, msg="ok")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error uploading audio: {e}")
        raise HTTPException(
            status_code=500,
            detail={"code": -1, "msg": str(e)}
        )

