"""
WebRTC related schemas
"""
from pydantic import BaseModel, Field
from typing import Optional


class OfferRequest(BaseModel):
    """WebRTC offer request"""
    sdp: str = Field(..., description="SDP offer string")
    type: str = Field(..., description="SDP type (offer)")


class OfferResponse(BaseModel):
    """WebRTC offer response"""
    sdp: str = Field(..., description="SDP answer string")
    type: str = Field(..., description="SDP type (answer)")
    sessionid: int = Field(..., description="Session ID")


class BaseResponse(BaseModel):
    """Base API response"""
    code: int = Field(..., description="Response code (0=success, -1=error)")
    msg: Optional[str] = Field(None, description="Response message")

