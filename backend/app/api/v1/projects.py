"""Project management endpoints."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.crud.project import project_crud
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectResponse,
    ProjectListResponse,
    ProjectDetailResponse,
    ScriptResponse,
    ScriptSceneResponse,
    CastResponse,
    CastAssignmentResponse,
    AssetResponse,
)
from app.models import ProjectStatus
from app.graph import run_pipeline
from app.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

# Hardcoded user ID for now (would come from auth in production)
DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


async def run_pipeline_background(
    project_id: str,
    user_id: str,
    script_prompt: str,
    auto_upload: bool
):
    """Background task to run the generation pipeline."""
    try:
        await run_pipeline(
            project_id=project_id,
            user_id=user_id,
            script_prompt=script_prompt,
            auto_upload=auto_upload,
            youtube_metadata=None
        )
    except Exception as e:
        logger.error(
            "Pipeline background task failed",
            project_id=project_id,
            error=str(e)
        )


@router.post("", response_model=ProjectResponse)
async def create_project(
    request: ProjectCreateRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new project and start generation pipeline.
    
    The pipeline runs in the background. Use WebSocket or polling
    to track progress.
    """
    # Create project record
    project = await project_crud.create(
        session=session,
        user_id=DEFAULT_USER_ID,
        title=request.title
    )

    # Update status to generating
    await project_crud.update_status(
        session=session,
        project_id=project.id,
        status=ProjectStatus.GENERATING_SCRIPT
    )

    # Start pipeline in background
    background_tasks.add_task(
        run_pipeline_background,
        project_id=str(project.id),
        user_id=str(DEFAULT_USER_ID),
        script_prompt=request.script_prompt,
        auto_upload=request.auto_upload
    )

    logger.info("Project created", project_id=str(project.id))

    return ProjectResponse(
        id=project.id,
        title=project.title,
        status=project.status.value,
        youtube_video_id=project.youtube_video_id,
        youtube_url=project.youtube_url,
        error_message=project.error_message,
        created_at=project.created_at,
        updated_at=project.updated_at
    )


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session)
):
    """List all projects for the current user."""
    items, total = await project_crud.list_by_user(
        session=session,
        user_id=DEFAULT_USER_ID,
        page=page,
        page_size=page_size
    )

    return ProjectListResponse(
        items=[
            ProjectResponse(
                id=p.id,
                title=p.title,
                status=p.status.value,
                youtube_video_id=p.youtube_video_id,
                youtube_url=p.youtube_url,
                error_message=p.error_message,
                created_at=p.created_at,
                updated_at=p.updated_at
            )
            for p in items
        ],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    """Get project details with all related data."""
    project = await project_crud.get_with_relations(
        session=session,
        project_id=project_id,
        user_id=DEFAULT_USER_ID
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Build response
    response = ProjectDetailResponse(
        id=project.id,
        title=project.title,
        status=project.status.value,
        youtube_video_id=project.youtube_video_id,
        youtube_url=project.youtube_url,
        error_message=project.error_message,
        created_at=project.created_at,
        updated_at=project.updated_at
    )

    # Add script if exists
    if project.scripts:
        latest_script = max(project.scripts, key=lambda s: s.version)
        scenes_data = latest_script.content.get("scenes", [])
        response.script = ScriptResponse(
            id=latest_script.id,
            version=latest_script.version,
            scenes=[
                ScriptSceneResponse(
                    speaker=s.get("speaker", ""),
                    line=s.get("line", ""),
                    duration=s.get("duration", 3.0)
                )
                for s in scenes_data
            ],
            created_at=latest_script.created_at
        )

    # Add cast if exists
    if project.casts:
        latest_cast = project.casts[-1]
        response.cast = CastResponse(
            id=latest_cast.id,
            assignments={
                name: CastAssignmentResponse(
                    voice_id=settings.get("voice_id", ""),
                    pitch=settings.get("pitch", "+0Hz"),
                    rate=settings.get("rate", "+0%")
                )
                for name, settings in latest_cast.assignments.items()
            },
            created_at=latest_cast.created_at
        )

    # Add assets
    response.assets = [
        AssetResponse(
            id=asset.id,
            asset_type=asset.asset_type.value,
            file_path=asset.file_path,
            url=f"/static/{asset.file_path}",
            character_name=asset.character_name,
            file_size_bytes=asset.file_size_bytes,
            created_at=asset.created_at
        )
        for asset in project.assets
    ]

    return response


@router.post("/{project_id}/regenerate-audio")
async def regenerate_audio(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session)
):
    """Regenerate audio with current cast settings."""
    project = await project_crud.get_by_id(
        session=session,
        project_id=project_id,
        user_id=DEFAULT_USER_ID
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # TODO: Implement partial pipeline re-run from audio_generator node
    # For now, return a placeholder response

    return {"message": "Audio regeneration started", "project_id": str(project_id)}


@router.post("/{project_id}/regenerate-video")
async def regenerate_video(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session)
):
    """Regenerate video with existing audio."""
    project = await project_crud.get_by_id(
        session=session,
        project_id=project_id,
        user_id=DEFAULT_USER_ID
    )
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # TODO: Implement partial pipeline re-run from video_composer node
    
    return {"message": "Video regeneration started", "project_id": str(project_id)}