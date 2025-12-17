"""Casting-related schemas."""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class VoiceSettingsInput(BaseModel):
    """Voice settings for a single character."""
    voice_id: str
    pitch: str = Field(default="+0Hz", pattern=r"^[+-]\d+Hz$")
    rate: str = Field(default="+0%", pattern=r"^[+-]\d+%$")


class CastUpdateRequest(BaseModel):
    """Request to update cast assignments."""
    assignments: Dict[str, VoiceSettingsInput]


class VoicePreviewRequest(BaseModel):
    """Request to generate a voice preview."""
    character: str
    voice_settings: VoiceSettingsInput
    sample_text: str = Field(..., max_length=500, min_length=1)


class VoicePreviewResponse(BaseModel):
    """Response with preview audio URL."""
    audio_url: str


class VoiceInfo(BaseModel):
    """Information about an available voice."""
    voice_id: str
    name: str
    gender: str
    locale: str


class VoiceListResponse(BaseModel):
    """List of available TTS voices."""
    voices: List[VoiceInfo]