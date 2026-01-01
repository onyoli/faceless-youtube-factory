"""
Scheduler API endpoints for managing scheduled video generation jobs.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.auth import ClerkUser, get_current_user
from app.models.scheduled_job import (
    ScheduledJob,
    ScheduledJobCreate,
    ScheduledJobRead,
    ScheduledJobUpdate,
)
from app.api.v1.projects import ensure_user_exists
from app.services.scheduler_service import (
    add_job_to_scheduler,
    remove_job_from_scheduler,
)
from app.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("", response_model=List[ScheduledJobRead])
async def list_scheduled_jobs(
    session: AsyncSession = Depends(get_session),
    current_user: ClerkUser = Depends(get_current_user),
):
    """List all scheduled jobs for the current user."""
    user_id = await ensure_user_exists(session, current_user)

    result = await session.execute(
        select(ScheduledJob)
        .where(ScheduledJob.user_id == user_id)
        .order_by(ScheduledJob.created_at.desc())
    )
    jobs = result.scalars().all()
    return jobs


@router.post("", response_model=ScheduledJobRead, status_code=status.HTTP_201_CREATED)
async def create_scheduled_job(
    job_data: ScheduledJobCreate,
    session: AsyncSession = Depends(get_session),
    current_user: ClerkUser = Depends(get_current_user),
):
    """Create a new scheduled job."""
    user_id = await ensure_user_exists(session, current_user)

    # Validate cron expression
    try:
        from apscheduler.triggers.cron import CronTrigger

        CronTrigger.from_crontab(job_data.cron_expression)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cron expression: {str(e)}",
        )

    # Create job in database
    job = ScheduledJob(
        **job_data.model_dump(),
        user_id=user_id,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    # Add to scheduler
    try:
        next_run = add_job_to_scheduler(job)
        job.next_run_at = next_run
        session.add(job)
        await session.commit()
        await session.refresh(job)
    except Exception as e:
        logger.error("Failed to add job to scheduler", error=str(e))

    logger.info("Scheduled job created", job_id=str(job.id), name=job.name)
    return job


@router.get("/{job_id}", response_model=ScheduledJobRead)
async def get_scheduled_job(
    job_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: ClerkUser = Depends(get_current_user),
):
    """Get a specific scheduled job."""
    user_id = await ensure_user_exists(session, current_user)

    result = await session.execute(
        select(ScheduledJob).where(
            ScheduledJob.id == job_id, ScheduledJob.user_id == user_id
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@router.patch("/{job_id}", response_model=ScheduledJobRead)
async def update_scheduled_job(
    job_id: UUID,
    job_data: ScheduledJobUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: ClerkUser = Depends(get_current_user),
):
    """Update a scheduled job."""
    user_id = await ensure_user_exists(session, current_user)

    result = await session.execute(
        select(ScheduledJob).where(
            ScheduledJob.id == job_id, ScheduledJob.user_id == user_id
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Update fields
    update_data = job_data.model_dump(exclude_unset=True)

    # Validate cron if changed
    if "cron_expression" in update_data:
        try:
            from apscheduler.triggers.cron import CronTrigger

            CronTrigger.from_crontab(update_data["cron_expression"])
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid cron expression: {str(e)}",
            )

    for key, value in update_data.items():
        setattr(job, key, value)

    session.add(job)
    await session.commit()

    # Update scheduler
    if job.is_active:
        try:
            next_run = add_job_to_scheduler(job)
            job.next_run_at = next_run
            session.add(job)
            await session.commit()
        except Exception as e:
            logger.error("Failed to update job in scheduler", error=str(e))
    else:
        remove_job_from_scheduler(str(job.id))

    await session.refresh(job)
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scheduled_job(
    job_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: ClerkUser = Depends(get_current_user),
):
    """Delete a scheduled job."""
    user_id = await ensure_user_exists(session, current_user)

    result = await session.execute(
        select(ScheduledJob).where(
            ScheduledJob.id == job_id, ScheduledJob.user_id == user_id
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Remove from scheduler
    remove_job_from_scheduler(str(job.id))

    # Delete from database
    await session.delete(job)
    await session.commit()

    logger.info("Scheduled job deleted", job_id=str(job_id))
