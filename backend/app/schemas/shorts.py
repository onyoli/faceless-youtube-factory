"""Shorts/TikTok project schemas."""

from typing import Optional, Literal
from pydantic import BaseModel, Field


class ShortsCreateRequest(BaseModel):
    """Request body for creating Shorts/TikTok project."""

    title: str = Field(..., max_length=255, min_length=1)
    script_prompt: str = Field(..., max_length=5000, min_length=10)

    # Background options
    background_mode: Literal[
        "image_per_scene", "image_single", "video", "image_upload", "none"
    ] = Field(
        default="video",
        description="Background mode: image_per_scene, image_single, video (upload), image_upload, or none",
    )
    scenes_per_image: int = Field(default=2, ge=1, le=10)
    background_video_url: Optional[str] = Field(
        default=None, description="Uploaded video URL for video mode"
    )
    background_image_url: Optional[str] = Field(
        default=None, description="Uploaded image URL for image_upload mode"
    )
    background_music_url: Optional[str] = Field(
        default=None, description="Background music URL"
    )
    music_volume: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Background music volume (0-1)"
    )
