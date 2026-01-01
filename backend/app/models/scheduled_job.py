"""
Scheduled job model for automated video generation.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel
from app.models.base import BaseUUIDModel


class ScheduledJobBase(SQLModel):
    """Base properties for scheduled jobs."""

    name: str = Field(max_length=255, description="Job name")
    cron_expression: str = Field(
        max_length=100, description="Cron schedule (e.g., '0 2 * * *' for 10 AM PH)"
    )
    topic_category: str = Field(
        max_length=1000, description="Category for topic generation"
    )
    video_format: str = Field(
        default="vertical", description="'horizontal' or 'vertical'"
    )
    auto_upload: bool = Field(
        default=True, description="Auto-upload to YouTube when complete"
    )
    is_active: bool = Field(default=True, description="Whether job is enabled")


class ScheduledJob(ScheduledJobBase, BaseUUIDModel, table=True):
    """
    Scheduled job database model.
    Table: scheduled_jobs
    """

    __tablename__ = "scheduled_jobs"

    # Owner of this scheduled job
    user_id: UUID = Field(foreign_key="users.id", index=True)

    # Tracking
    last_run_at: Optional[datetime] = Field(
        default=None, description="Last execution time"
    )
    next_run_at: Optional[datetime] = Field(
        default=None, description="Next scheduled run"
    )
    run_count: int = Field(default=0, description="Number of successful runs")


class ScheduledJobCreate(ScheduledJobBase):
    """Schema for creating a scheduled job."""

    pass


class ScheduledJobRead(ScheduledJobBase):
    """Schema for reading a scheduled job."""

    id: UUID
    user_id: UUID
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    run_count: int
    created_at: datetime


class ScheduledJobUpdate(SQLModel):
    """Schema for updating a scheduled job."""

    name: Optional[str] = None
    cron_expression: Optional[str] = None
    topic_category: Optional[str] = None
    video_format: Optional[str] = None
    auto_upload: Optional[bool] = None
    is_active: Optional[bool] = None
