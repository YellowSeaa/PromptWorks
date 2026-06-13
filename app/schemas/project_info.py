from __future__ import annotations

from pydantic import BaseModel, Field


class ProjectMetadata(BaseModel):
    name: str
    description: str
    github_url: str
    contact_email: str
    tutorial_available: bool = False


class ProjectStatistics(BaseModel):
    provider_count: int = Field(ge=0)
    model_count: int = Field(ge=0)
    prompt_count: int = Field(ge=0)
    prompt_version_count: int = Field(ge=0)
    test_task_count: int = Field(ge=0)
    test_unit_count: int = Field(ge=0)
    test_experiment_count: int = Field(ge=0)


class ProjectUpdateGuidance(BaseModel):
    deployment_type: str
    title: str
    steps: list[str]
    commands: list[str] = Field(default_factory=list)


class ProjectVersionInfo(BaseModel):
    current: str
    latest: str | None = None
    has_update: bool = False
    check_status: str = "unknown"
    check_error: str | None = None
    release_url: str | None = None
    deployment_type: str
    update_guidance: ProjectUpdateGuidance


class ProjectInfoSummary(BaseModel):
    project: ProjectMetadata
    version: ProjectVersionInfo
    statistics: ProjectStatistics
