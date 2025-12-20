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
    project_id: str, user_id: str, script_prompt: str, auto_upload: bool
):
    """Background task to run the generation pipeline."""
    try:
        await run_pipeline(
            project_id=project_id,
            user_id=user_id,
            script_prompt=script_prompt,
            auto_upload=auto_upload,
            youtube_metadata=None,
        )
    except Exception as e:
        logger.error(
            "Pipeline background task failed", project_id=project_id, error=str(e)
        )


@router.post("", response_model=ProjectResponse)
async def create_project(
    request: ProjectCreateRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new project and start generation pipeline.

    The pipeline runs in the background. Use WebSocket or polling
    to track progress.
    """
    # Create project record
    project = await project_crud.create(
        session=session, user_id=DEFAULT_USER_ID, title=request.title
    )

    # Update status to generating
    await project_crud.update_status(
        session=session, project_id=project.id, status=ProjectStatus.GENERATING_SCRIPT
    )

    # Start pipeline in background
    background_tasks.add_task(
        run_pipeline_background,
        project_id=str(project.id),
        user_id=str(DEFAULT_USER_ID),
        script_prompt=request.script_prompt,
        auto_upload=request.auto_upload,
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
        updated_at=project.updated_at,
    )


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """List all projects for the current user."""
    items, total = await project_crud.list_by_user(
        session=session, user_id=DEFAULT_USER_ID, page=page, page_size=page_size
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
                updated_at=p.updated_at,
            )
            for p in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(project_id: UUID, session: AsyncSession = Depends(get_session)):
    """Get project details with all related data."""
    project = await project_crud.get_with_relations(
        session=session, project_id=project_id, user_id=DEFAULT_USER_ID
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
        updated_at=project.updated_at,
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
                    duration=s.get("duration", 3.0),
                )
                for s in scenes_data
            ],
            created_at=latest_script.created_at,
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
                    rate=settings.get("rate", "+0%"),
                )
                for name, settings in latest_cast.assignments.items()
            },
            created_at=latest_cast.created_at,
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
            created_at=asset.created_at,
        )
        for asset in project.assets
    ]

    return response


@router.post("/{project_id}/regenerate-audio")
async def regenerate_audio(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """Regenerate audio with current cast settings."""
    from app.graph.nodes.audio_generator import audio_generator_node
    from app.graph.nodes.video_composer import video_composer_node
    from app.models import Asset, AssetType
    from sqlmodel import delete

    project = await project_crud.get_by_id(
        session=session, project_id=project_id, user_id=DEFAULT_USER_ID
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.scripts or not project.casts:
        raise HTTPException(
            status_code=400,
            detail="Project needs script and cast before regenerating audio",
        )

    # Get latest script and cast
    latest_script = max(project.scripts, key=lambda s: s.version)
    latest_cast = project.casts[-1]

    # Delete existing audio assets
    await session.execute(
        delete(Asset).where(
            Asset.project_id == project_id, Asset.asset_type == AssetType.AUDIO
        )
    )
    await session.commit()

    # Build state for audio regeneration
    async def regenerate_task():
        from app.graph.state import GraphState

        state: GraphState = {
            "project_id": str(project_id),
            "user_id": str(DEFAULT_USER_ID),
            "script_prompt": "",
            "auto_upload": False,
            "script_json": latest_script.content,
            "cast_list": latest_cast.assignments,
            "audio_files": [],
            "video_path": None,
            "youtube_metadata": None,
            "youtube_video_id": None,
            "errors": [],
            "retry_count": 0,
            "current_step": "regenerating_audio",
            "progress": 0.3,
        }

        # Run audio generator
        state = await audio_generator_node(state)

        # Run video composer if audio succeded
        if state["audio_files"]:
            state = await video_composer_node(state)

        logger.info(
            "Audio regeneration complete",
            project_id=str(project_id),
            audio_count=len(state["audio_files"]),
        )

    background_tasks.add_task(regenerate_task)

    return {"message": "Audio regeneration started", "project_id": str(project_id)}


@router.post("/{project_id}/regenerate-video")
async def regenerate_video(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """Regenerate video with existing audio."""
    from app.graph.nodes.video_composer import video_composer_node
    from app.models import Asset, AssetType
    from sqlmodel import select, delete

    project = await project_crud.get_by_id(
        session=session, project_id=project_id, user_id=DEFAULT_USER_ID
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get audio assets
    audio_assets = [a for a in project.assets if a.asset_type == AssetType.AUDIO]

    if not audio_assets:
        raise HTTPException(
            status_code=400, detail="No audio files to compose into video"
        )

    # Get script for metadata
    if not project.scripts:
        raise HTTPException(status_code=400, detail="No script found")

    latest_script = max(project.scripts, key=lambda s: s.version)

    # Delete existing video assets
    await session.execute(
        delete(Asset).where(
            Asset.project_id == project_id, Asset.asset_type == AssetType.VIDEO
        )
    )
    await session.commit()

    # Sort audio files by scene index
    audio_files = sorted(
        [a.file_path for a in audio_assets],
        key=lambda p: int(p.split("/")[-1].replace(".mp3", "")),
    )

    async def regenerate_task():
        from app.graph.state import GraphState

        state: GraphState = {
            "project_id": str(project_id),
            "user_id": str(DEFAULT_USER_ID),
            "script_prompt": "",
            "auto_upload": False,
            "script_json": latest_script.content,
            "cast_list": {},
            "audio_files": audio_files,
            "video_path": None,
            "youtube_metadata": None,
            "youtube_video_id": None,
            "errors": [],
            "retry_count": 0,
            "current_step": "regenerating_video",
            "progress": 0.6,
        }

        state = await video_composer_node(state)

        logger.info(
            "Video regeneration complete",
            project_id=str(project_id),
            video_path=state.get("video_path"),
        )

    background_tasks.add_task(regenerate_task)

    return {"message": "Video regeneration started", "project_id": str(project_id)}


@router.post("/{project_id}/cancel")
async def cancel_project(
    project_id: UUID, session: AsyncSession = Depends(get_session)
):
    """
    Cancel an in-progress project.

    Sets the project status to 'failed' with a cancellation message.
    Note: This doesn't stop a running background task immediately,
    but prevents further processing steps.
    """
    project = await project_crud.get_by_id(
        session=session, project_id=project_id, user_id=DEFAULT_USER_ID
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if project is in a cancellable state
    cancellable_states = [
        ProjectStatus.DRAFT,
        ProjectStatus.GENERATING_SCRIPT,
        ProjectStatus.CASTING,
        ProjectStatus.GENERATING_IMAGES,
        ProjectStatus.GENERATING_AUDIO,
        ProjectStatus.GENERATING_VIDEO,
        ProjectStatus.UPLOADING_YOUTUBE,
    ]

    if project.status not in cancellable_states:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel project in '{project.status.value}' status",
        )

    # Update status to failed with cancellation message
    project.status = ProjectStatus.FAILED
    project.error_message = "Cancelled by user"
    session.add(project)
    await session.commit()

    logger.info("Project cancelled", project_id=str(project_id))

    return {"message": "Project cancelled", "project_id": str(project_id)}


@router.delete("/{project_id}")
async def delete_project(
    project_id: UUID, session: AsyncSession = Depends(get_session)
):
    """
    Delete a project and all its related data.

    Removes:
    - Project record
    - Scripts, casts, assets from database
    - Generated files from filesystem
    """
    from app.models import Project, Script, Cast, Asset
    from sqlmodel import delete
    import shutil
    from pathlib import Path
    from app.config import settings

    project = await project_crud.get_by_id(
        session=session, project_id=project_id, user_id=DEFAULT_USER_ID
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Don't allow deletion of in-progress projects
    in_progress_states = [
        ProjectStatus.GENERATING_SCRIPT,
        ProjectStatus.CASTING,
        ProjectStatus.GENERATING_IMAGES,
        ProjectStatus.GENERATING_AUDIO,
        ProjectStatus.GENERATING_VIDEO,
        ProjectStatus.UPLOADING_YOUTUBE,
    ]

    if project.status in in_progress_states:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete project while in progress. Cancel it first.",
        )

    # Delete generated files
    static_dir = Path(settings.static_dir)

    # Delete audio files
    audio_dir = static_dir / "audio" / str(project_id)
    if audio_dir.exists():
        shutil.rmtree(audio_dir, ignore_errors=True)
        logger.info(f"Deleted audio directory: {audio_dir}")

    # Delete video files
    video_dir = static_dir / "video" / str(project_id)
    if video_dir.exists():
        shutil.rmtree(video_dir, ignore_errors=True)
        logger.info(f"Deleted video directory: {video_dir}")

    # Delete image files
    images_dir = static_dir / "images" / str(project_id)
    if images_dir.exists():
        shutil.rmtree(images_dir, ignore_errors=True)
        logger.info(f"Deleted images directory: {images_dir}")

    # Delete database records (cascading deletes handle related records)
    await session.execute(delete(Asset).where(Asset.project_id == project_id))
    await session.execute(delete(Cast).where(Cast.project_id == project_id))
    await session.execute(delete(Script).where(Script.project_id == project_id))
    await session.execute(delete(Project).where(Project.id == project_id))
    await session.commit()

    logger.info("Project deleted", project_id=str(project_id))

    return {"message": "Project deleted successfully", "project_id": str(project_id)}
