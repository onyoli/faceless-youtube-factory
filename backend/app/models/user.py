"""
User model for multi-user support.
"""
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID
from sqlmodel import Field, Relationship, SQLModel
from app.models.base import BaseUUIDModel

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.youtube_connection import YouTubeConnection


class UserBase(SQLModel):
    """Shared user properties."""
    email: str = Field(
        max_length=255,
        unique=True,
        index=True,
        nullable=False
    )


class User(UserBase, BaseUUIDModel, table=True):
    """
    User database model.
    Table: users
    """
    __tablename__ = "users"

    # Relationships
    projects: List["Project"] = Relationship(back_populates="user")
    youtube_connections: List["YouTubeConnection"] = Relationship(back_populates="user")


class UserCreate(UserBase):
    """Schema for creating a new user."""
    pass


class UserRead(UserBase):
    """Schema for reading user data."""
    id: UUID
    created_at: datetime