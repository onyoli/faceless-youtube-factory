"""YouTube-related schemas."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.models.enums import PrivacyStatus


class YouTubeAuthUrlResponse(BaseModel):
    """OAuth authorization URL response."""
    auth_url: str
    state: str


class YouTubeConnectionResponse(BaseModel):
    """YouTube connection status response."""
    connected: bool
    channel_id: Optional[str] = None
    channel_title: Optional[str] = None


class YouTubeMetadataRequest(BaseModel):
    """Request to generate or update YouTube metadata."""
    video_context: Optional[str] = Field(default=None, max_length=1000)


class YouTubeMetadataResponse(BaseModel):
    """Generated YouTube metadata."""
    title: str = Field(..., max_length=100)
    description: str
    tags: List[str]
    category_id: str


class YouTubeUploadRequest(BaseModel):
    """Request to upload video to YouTube."""
    title: str = Field(..., max_length=100, min_length=1)
    description: str = Field(default="")
    tags: List[str] = Field(default_factory=list, max_length=15)
    category_id: str = Field(default="22")
    privacy_status: PrivacyStatus = PrivacyStatus.PRIVATE


class YouTubeQuotaResponse(BaseModel):
    """YouTube quota status."""
    uploads_today: int
    limit: int
    resets_at: datetime