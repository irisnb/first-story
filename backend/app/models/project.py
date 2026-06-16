"""Project metadata model.

This defines the project-level configuration and metadata.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class Project(BaseModel):
    """Project metadata."""

    id: str = Field(..., description="Unique project identifier")
    name: str = Field(..., description="Project display name")
    created_at: datetime = Field(..., description="ISO 8601 creation timestamp")
    updated_at: datetime = Field(..., description="ISO 8601 last update timestamp")
    version: str = Field(default="1.0.0", description="Schema version for project metadata")
