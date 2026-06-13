from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.llm_provider import LLMModel, LLMProvider
from app.models.prompt import Prompt, PromptVersion
from app.models.prompt_test import PromptTestExperiment, PromptTestTask, PromptTestUnit
from app.schemas.project_info import (
    ProjectInfoSummary,
    ProjectMetadata,
    ProjectStatistics,
    ProjectUpdateGuidance,
    ProjectVersionInfo,
)

PROJECT_DESCRIPTION = (
    "PromptWorks 是一个聚焦 Prompt 资产管理与大模型运营的全栈解决方案，"
    "支持 Prompt 生命周期管理、模型配置、版本对比与评估实验。"
)
GITHUB_URL = "https://github.com/YellowSeaa/PromptWorks"
GITHUB_LATEST_RELEASE_API = (
    "https://api.github.com/repos/YellowSeaa/PromptWorks/releases/latest"
)
DEFAULT_CONTACT_EMAIL = "hh81300889@gmail.com"
DEFAULT_VERSION = "v0.0.0"
VERSION_PATTERN = re.compile(
    r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?:-(?P<pre>[0-9A-Za-z.-]+))?$"
)


def read_current_version() -> str:
    """读取当前版本号，优先使用部署环境显式注入的版本。"""

    env_version = os.getenv("PROMPTWORKS_VERSION")
    if env_version:
        return normalize_version(env_version)

    version_file = (
        Path(__file__).resolve().parents[2] / "frontend" / "src" / "version.json"
    )
    if version_file.exists():
        try:
            data = json.loads(version_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return DEFAULT_VERSION
        version = data.get("version")
        if isinstance(version, str) and version.strip():
            return normalize_version(version)
    return DEFAULT_VERSION


def normalize_version(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        return DEFAULT_VERSION
    return trimmed if trimmed.startswith("v") else f"v{trimmed}"


def parse_version(value: str) -> tuple[int, int, int, tuple[int, str | None, str]]:
    normalized = normalize_version(value)
    match = VERSION_PATTERN.match(normalized)
    if not match:
        return (0, 0, 0, (0, None, normalized))

    prerelease = match.group("pre")
    prerelease_rank = (1, None, "") if prerelease is None else (0, prerelease, "")
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        prerelease_rank,
    )


def is_newer_version(latest: str | None, current: str) -> bool:
    if not latest:
        return False
    return parse_version(latest) > parse_version(current)


def resolve_check_status(
    *, latest: str | None, current: str, check_failed: bool
) -> str:
    if check_failed:
        return "failed"
    if not latest:
        return "unknown"
    return "update_available" if is_newer_version(latest, current) else "up_to_date"


def detect_deployment_type() -> str:
    explicit = os.getenv("PROMPTWORKS_DEPLOYMENT_TYPE")
    if explicit:
        normalized = explicit.strip().lower()
        if normalized in {"source", "docker"}:
            return normalized

    if os.getenv("KUBERNETES_SERVICE_HOST") or Path("/.dockerenv").exists():
        return "docker"
    if (Path.cwd() / ".git").exists():
        return "source"
    return "unknown"


def build_update_guidance(deployment_type: str) -> ProjectUpdateGuidance:
    if deployment_type == "docker":
        return ProjectUpdateGuidance(
            deployment_type=deployment_type,
            title="Docker 部署更新命令",
            steps=[
                "在部署目录复制并执行以下命令，拉取最新镜像并重启服务。",
                "更新完成后重新打开项目信息页，确认当前版本已变化。",
            ],
            commands=[
                "docker compose pull",
                "docker compose up -d",
            ],
        )
    if deployment_type == "source":
        return ProjectUpdateGuidance(
            deployment_type=deployment_type,
            title="源码部署更新命令",
            steps=[
                "在源码目录确认无未保存改动后，复制并执行以下命令更新代码与依赖。",
                "更新完成后重启后端与前端服务，并再次检查版本。",
            ],
            commands=[
                "git pull --ff-only",
                "uv sync",
                "npm --prefix frontend ci",
                "uv run alembic upgrade head",
            ],
        )
    return ProjectUpdateGuidance(
        deployment_type=deployment_type,
        title="更新命令待确认",
        steps=[
            "当前环境无法可靠识别源码部署或 Docker 部署。",
            "请先确认实际部署方式，再查看发布说明中的更新步骤。",
        ],
        commands=[],
    )


def get_project_metadata() -> ProjectMetadata:
    return ProjectMetadata(
        name=settings.PROJECT_NAME,
        description=PROJECT_DESCRIPTION,
        github_url=GITHUB_URL,
        contact_email=os.getenv("PROMPTWORKS_CONTACT_EMAIL", DEFAULT_CONTACT_EMAIL),
        tutorial_available=False,
    )


def get_project_statistics(db: Session) -> ProjectStatistics:
    def count(stmt: Any) -> int:
        return int(db.scalar(stmt) or 0)

    active_provider_ids = select(LLMProvider.id).where(
        LLMProvider.is_archived.is_(False)
    )
    return ProjectStatistics(
        provider_count=count(
            select(func.count())
            .select_from(LLMProvider)
            .where(LLMProvider.is_archived.is_(False))
        ),
        model_count=count(
            select(func.count())
            .select_from(LLMModel)
            .where(LLMModel.provider_id.in_(active_provider_ids))
        ),
        prompt_count=count(select(func.count()).select_from(Prompt)),
        prompt_version_count=count(select(func.count()).select_from(PromptVersion)),
        test_task_count=count(
            select(func.count())
            .select_from(PromptTestTask)
            .where(PromptTestTask.is_deleted.is_(False))
        ),
        test_unit_count=count(select(func.count()).select_from(PromptTestUnit)),
        test_experiment_count=count(
            select(func.count()).select_from(PromptTestExperiment)
        ),
    )


def get_project_version_info(
    *,
    latest: str | None = None,
    release_url: str | None = None,
    check_failed: bool = False,
    check_error: str | None = None,
) -> ProjectVersionInfo:
    current = read_current_version()
    deployment_type = detect_deployment_type()
    normalized_latest = normalize_version(latest) if latest else None
    check_status = resolve_check_status(
        latest=normalized_latest, current=current, check_failed=check_failed
    )
    return ProjectVersionInfo(
        current=current,
        latest=normalized_latest,
        has_update=is_newer_version(normalized_latest, current),
        check_status=check_status,
        check_error=check_error,
        release_url=release_url,
        deployment_type=deployment_type,
        update_guidance=build_update_guidance(deployment_type),
    )


def build_project_info_summary(db: Session) -> ProjectInfoSummary:
    return ProjectInfoSummary(
        project=get_project_metadata(),
        version=get_project_version_info(),
        statistics=get_project_statistics(db),
    )


def check_latest_project_version() -> ProjectVersionInfo:
    try:
        response = httpx.get(
            GITHUB_LATEST_RELEASE_API,
            timeout=5.0,
            headers={"Accept": "application/vnd.github+json"},
        )
    except httpx.HTTPError:
        return get_project_version_info(
            check_failed=True,
            check_error="github_unavailable",
        )

    if response.status_code >= 400:
        rate_remaining = response.headers.get("x-ratelimit-remaining")
        check_error = (
            "github_rate_limited"
            if response.status_code in {403, 429} and rate_remaining == "0"
            else "github_unavailable"
        )
        return get_project_version_info(check_failed=True, check_error=check_error)

    payload = response.json()
    latest = payload.get("tag_name")
    release_url = payload.get("html_url")
    return get_project_version_info(
        latest=latest if isinstance(latest, str) else None,
        release_url=release_url if isinstance(release_url, str) else None,
    )
