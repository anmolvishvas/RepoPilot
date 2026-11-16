"""Pydantic v2 schemas for FastAPI gateway endpoints and streaming events."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MigrationCreateRequest(BaseModel):
    """Payload for submitting a new codebase migration task."""

    model_config = ConfigDict(strict=True)

    repo_path: str = Field(
        min_length=1, description="Absolute or relative path to target repository"
    )
    recipe: str = Field(
        min_length=1, description="Modernization recipe or prompt (e.g. 'sync-to-async')"
    )
    max_retries: int = Field(
        default=3, ge=1, le=10, description="Maximum self-healing retry budget"
    )
    target_files: list[str] = Field(
        default_factory=list, description="Optional restricted target file subset"
    )


class MigrationSummaryResponse(BaseModel):
    """Summary snapshot of an active or completed migration workflow."""

    model_config = ConfigDict(strict=True)

    task_id: str
    phase: str
    is_terminal: bool
    retry_count: int
    patches_count: int
    affected_files: list[str]
    error_message: str | None = None


class ApprovalRequest(BaseModel):
    """Payload for human-in-the-loop operator approval or rejection."""

    model_config = ConfigDict(strict=True)

    approved: bool
    operator: str = Field(default="human_operator")
    comment: str | None = None


class HealthResponse(BaseModel):
    """Health check response schema."""

    model_config = ConfigDict(strict=True)

    status: str = "ok"
    version: str = "0.1.0"
    uptime_seconds: float = 0.0
