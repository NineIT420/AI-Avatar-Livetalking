"""
Recording related schemas
"""
from pydantic import BaseModel, Field
from typing import Literal


class RecordRequest(BaseModel):
    """Recording request"""
    type: Literal["start_record", "end_record"] = Field(..., description="Recording action")
    sessionid: int = Field(..., description="Session ID")


class IsSpeakingRequest(BaseModel):
    """Is speaking request"""
    sessionid: int = Field(..., description="Session ID")


class IsSpeakingResponse(BaseModel):
    """Is speaking response"""
    code: int = Field(..., description="Response code")
    data: bool = Field(..., description="Is speaking status")

