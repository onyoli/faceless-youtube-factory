"""
Script model - stores generated video scripts as JSONB.
"""
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

from sqlmodel import Field, Relationship, SQLModel, Column
from sqlalchemy import JSON

from app.models.base import BaseUUIDModel

if TYPE_CHECKING:
    from app.models.project import Project


class SceneContent(SQLModel):
    """
    Schema for a single scene in the script.
    
    Structure: {"speaker": "string", "line": "string", "duration": float}
    """
    speaker: str
    line: str
    duration: float = Field(default=3.0, ge=0.5, le=60.0)


class ScriptContent(SQLModel):
    """
    Schema for the full script content.
    
    Structure: {"scenes": [SceneContent, ...]}
    """
    scenes: List[SceneContent] = []


class ScriptBase(SQLModel):
    """Shared script properties."""
    version: int = Field(default=1, ge=1)


class Script(ScriptBase, BaseUUIDModel, table=True):
    """
    Script database model.
    
    Table: scripts
    
    Stores the generated video script with scene/speaker structure.
    The content column is JSONB for flexible querying.
    """
    __tablename__ = "scripts"

    # Foreign key to project
    project_id: UUID = Field(foreign_key="projects.id", nullable=False, index=True)

    # JSONB content column
    content: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False)
    )

    # Relationships
    project: Optional["Project"] = Relationship(back_populates="scripts")

    def get_scenes(self) -> List[SceneContent]:
        """Parse content into SceneContent objects."""
        scenes_data = self.content.get("scenes", [])
        return [SceneContent(**scene) for scene in scenes_data]

    def get_speakers(self) -> List[str]:
        """Extract unique speaker names from the script."""
        scenes = self.get_scenes()
        return list(set(scene.speaker for scene in scenes))

    
class ScriptCreate(SQLModel):
    """Schema for creating a new script."""
    project_id: UUID
    content: Dict[str, Any]
    version: int = 1


class ScriptRead(ScriptBase):
    """Schema for reading script data."""
    id: UUID
    project_id: UUID
    content: Dict[str, Any]
    created_at: datetime