"""
Scheduler service for automated video generation.
Uses APScheduler to run cron jobs that create projects automatically.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.database import get_session_context
from app.models.scheduled_job import ScheduledJob
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


async def generate_topic_from_category(category: str) -> str:
    """
    Use Groq LLM to generate a specific video topic from a category.
    """
    from langchain_groq import ChatGroq

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.9,  # High creativity for unique topics
        api_key=settings.groq_api_key,
    )

    prompt = f"""Generate a unique, engaging video topic for a short-form video (YouTube Shorts/TikTok/Reels).

Category: {category}

Requirements:
- Be specific and interesting
- Should work as a 30-90 second video
- Should hook viewers in the first few seconds
- Don't include hashtags or emojis

Return ONLY the topic/title, nothing else. One line."""

    response = await llm.ainvoke(prompt)
    topic = response.content.strip().strip('"').strip("'")
    logger.info("Generated topic from category", category=category, topic=topic)
    return topic


async def run_scheduled_job(job_id: str, user_id: str):
    """
    Execute a scheduled job - generate topic, create project, start pipeline.
    """
    from app.crud import project as project_crud
    from app.models import ProjectStatus
    from app.api.v1.projects import run_pipeline_background

    logger.info("Running scheduled job", job_id=job_id, user_id=user_id)

    async with get_session_context() as session:
        # Get the job
        result = await session.execute(
            select(ScheduledJob).where(ScheduledJob.id == UUID(job_id))
        )
        job = result.scalar_one_or_none()

        if not job or not job.is_active:
            logger.warning("Job not found or inactive", job_id=job_id)
            return

        try:
            # Generate topic from category
            topic = await generate_topic_from_category(job.topic_category)

            # Create project
            title = f"Auto: {topic[:50]}" if len(topic) > 50 else f"Auto: {topic}"
            project = await project_crud.create(
                session=session, user_id=UUID(user_id), title=title
            )

            # Update status
            await project_crud.update_status(
                session=session,
                project_id=project.id,
                status=ProjectStatus.GENERATING_SCRIPT,
            )

            # Update job tracking
            job.last_run_at = datetime.now(timezone.utc)
            job.run_count += 1
            session.add(job)
            await session.commit()

            logger.info(
                "Scheduled project created",
                job_id=job_id,
                project_id=str(project.id),
                topic=topic,
            )

            # Run pipeline in background
            asyncio.create_task(
                run_pipeline_background(
                    project_id=str(project.id),
                    user_id=user_id,
                    script_prompt=topic,
                    auto_upload=job.auto_upload,
                    video_format=job.video_format,
                    enable_captions=True,
                )
            )

        except Exception as e:
            logger.error("Scheduled job failed", job_id=job_id, error=str(e))


def add_job_to_scheduler(job: ScheduledJob):
    """Add a scheduled job to the APScheduler."""
    scheduler = get_scheduler()

    try:
        trigger = CronTrigger.from_crontab(job.cron_expression)

        scheduler.add_job(
            run_scheduled_job,
            trigger=trigger,
            id=str(job.id),
            args=[str(job.id), str(job.user_id)],
            replace_existing=True,
            name=job.name,
        )

        # Get next run time
        next_run = trigger.get_next_fire_time(None, datetime.now(timezone.utc))
        logger.info(
            "Job added to scheduler",
            job_id=str(job.id),
            name=job.name,
            next_run=str(next_run),
        )
        return next_run

    except Exception as e:
        logger.error("Failed to add job to scheduler", job_id=str(job.id), error=str(e))
        raise


def remove_job_from_scheduler(job_id: str):
    """Remove a job from the scheduler."""
    scheduler = get_scheduler()
    try:
        scheduler.remove_job(job_id)
        logger.info("Job removed from scheduler", job_id=job_id)
    except Exception as e:
        logger.warning("Job not found in scheduler", job_id=job_id, error=str(e))


async def load_scheduled_jobs():
    """Load all active scheduled jobs from database into scheduler."""
    async with get_session_context() as session:
        result = await session.execute(
            select(ScheduledJob).where(ScheduledJob.is_active == True)
        )
        jobs = result.scalars().all()

        for job in jobs:
            try:
                next_run = add_job_to_scheduler(job)
                job.next_run_at = next_run
                session.add(job)
            except Exception as e:
                logger.error("Failed to load job", job_id=str(job.id), error=str(e))

        await session.commit()
        logger.info(f"Loaded {len(jobs)} scheduled jobs")


async def start_scheduler():
    """Start the scheduler and load jobs."""
    scheduler = get_scheduler()

    if not scheduler.running:
        await load_scheduled_jobs()
        scheduler.start()
        logger.info("Scheduler started")


def stop_scheduler():
    """Stop the scheduler."""
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
