"""Project-related schemas."""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    """Request body for creating a new project."""

    title: str = Field(..., max_length=255, min_length=1)
    script_prompt: str = Field(..., max_length=5000, min_length=10)
    auto_upload: bool = False
    image_mode: Literal["per_scene", "single", "upload", "none"] = Field(
        default="per_scene",
        description="Image generation mode: per_scene (ratio-based), single (one for entire video), upload (custom image), none (solid backgrounds)",
    )
    scenes_per_image: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Number of scenes per generated image (only used when image_mode='per_scene')",
    )
    background_image_url: Optional[str] = Field(
        default=None,
        description="URL/path of uploaded background image (only used when image_mode='upload')",
    )


class ProjectResponse(BaseModel):
    """Basic project response."""

    id: UUID
    title: str
    status: str
    youtube_video_id: Optional[str] = None
    youtube_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScriptSceneResponse(BaseModel):
    """A single scene in the script."""

    speaker: str
    line: str
    duration: float


class ScriptResponse(BaseModel):
    """Script data response."""

    id: UUID
    version: int
    scenes: List[ScriptSceneResponse]
    created_at: datetime


class CastAssignmentResponse(BaseModel):
    """Voice assignment for a character."""

    voice_id: str
    pitch: str
    rate: str


class CastResponse(BaseModel):
    """Cast data response."""

    id: UUID
    assignments: Dict[str, CastAssignmentResponse]
    created_at: datetime


class AssetResponse(BaseModel):
    """Asset data response."""

    id: UUID
    asset_type: str
    file_path: str
    url: str
    character_name: Optional[str] = None
    file_size_bytes: Optional[int] = None
    created_at: datetime


class YouTubeMetadataShortResponse(BaseModel):
    """YouTube metadata in project response."""

    title: str
    privacy_status: str
    category_id: str


class ProjectDetailResponse(ProjectResponse):
    """Detailed project response with all related data."""

    script: Optional[ScriptResponse] = None
    cast: Optional[CastResponse] = None
    assets: List[AssetResponse] = []
    youtube_metadata: Optional[YouTubeMetadataShortResponse] = None


class ProjectListResponse(BaseModel):
    """Paginated list of projects."""

    items: List[ProjectResponse]
    total: int
    page: int
    page_size: int
