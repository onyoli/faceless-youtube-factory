"""Voice casting endpoints."""

import asyncio
from pathlib import Path
from uuid import UUID, uuid4
import hashlib

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.crud.project import project_crud
from app.schemas.cast import (
    CastUpdateRequest,
    VoicePreviewRequest,
    VoicePreviewResponse,
    VoiceListResponse,
    VoiceInfo,
)
from app.services.tts_service import tts_service
from app.models import Cast
from app.config import settings
from app.utils.logging import get_logger
from app.auth import ClerkUser, get_current_user

router = APIRouter()
logger = get_logger(__name__)


def get_user_uuid(clerk_user: ClerkUser) -> UUID:
    """Convert Clerk user ID to UUID for database operations."""
    hash_bytes = hashlib.md5(clerk_user.user_id.encode()).digest()
    return UUID(bytes=hash_bytes)


@router.get("/voices", response_model=VoiceListResponse)
async def list_voices():
    """List all available TTS voices."""
    voices = await tts_service.get_voices()

    return VoiceListResponse(
        voices=[
            VoiceInfo(
                voice_id=v["voice_id"],
                name=v["name"],
                gender=v["gender"],
                locale=v["locale"],
            )
            for v in voices
        ]
    )


@router.put("/projects/{project_id}/cast")
async def update_cast(
    project_id: UUID,
    request: CastUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: ClerkUser = Depends(get_current_user),
):
    """
    Update voice cast assignments for a project.

    This will trigger audio regeneration.
    """
    user_id = get_user_uuid(current_user)
    project = await project_crud.get_by_id(
        session=session, project_id=project_id, user_id=user_id
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Convert assignment models to dict
    assignments_dict = {
        name: {"voice_id": vs.voice_id, "pitch": vs.pitch, "rate": vs.rate}
        for name, vs in request.assignments.items()
    }

    # Create new cast record
    cast = Cast(id=uuid4(), project_id=project_id, assignments=assignments_dict)
    session.add(cast)
    await session.commit()

    logger.info("Cast updated", project_id=str(project_id))

    return {
        "message": "Cast updated successfully",
        "project_id": str(project_id),
        "characters": list(assignments_dict.keys()),
    }


async def cleanup_preview(file_path: str, delay_seconds: int = 120):
    """Delete preview file after delay."""
    await asyncio.sleep(delay_seconds)
    try:
        path = Path(settings.static_dir) / "previews" / file_path
        if path.exists():
            path.unlink()
            logger.debug("Preview file cleaned up", path=str(path))
    except Exception as e:
        logger.warning("Failed to cleanup preview", error=str(e))


@router.post(
    "/projects/{project_id}/preview-voice", response_model=VoicePreviewResponse
)
async def preview_voice(
    project_id: UUID,
    request: VoicePreviewRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    current_user: ClerkUser = Depends(get_current_user),
):
    """
    Generate a temporary voice preview.

    The audio file is automatically deleted after 2 minutes.
    """
    # Verify project exists
    user_id = get_user_uuid(current_user)
    project = await project_crud.get_by_id(
        session=session, project_id=project_id, user_id=user_id
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        # Generate preview audio
        audio_path = await tts_service.generate_preview(
            text=request.sample_text,
            voice_id=request.voice_settings.voice_id,
            rate=request.voice_settings.rate,
            pitch=request.voice_settings.pitch,
        )

        # Schedule cleanup
        filename = Path(audio_path).name
        background_tasks.add_task(
            cleanup_preview, filename, settings.preview_cleanup_minutes * 60
        )

        return VoicePreviewResponse(audio_url=f"/static/{audio_path}")

    except Exception as e:
        logger.error("Voice preview failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to generate preview: {str(e)}"
        )
