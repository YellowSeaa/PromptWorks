from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.project_info import ProjectInfoSummary, ProjectVersionInfo
from app.services.project_info import (
    build_project_info_summary,
    check_latest_project_version,
)

router = APIRouter()


@router.get("/summary", response_model=ProjectInfoSummary)
def read_project_info_summary(*, db: Session = Depends(get_db)) -> ProjectInfoSummary:
    """读取项目说明、版本信息与资产统计。"""

    return build_project_info_summary(db)


@router.get("/version/check", response_model=ProjectVersionInfo)
def check_project_version() -> ProjectVersionInfo:
    """检查 GitHub Release 最新版本，并返回更新指引。"""

    return check_latest_project_version()
