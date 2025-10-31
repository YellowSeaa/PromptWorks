from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.settings import TestingTimeoutsRead, TestingTimeoutsUpdate
from app.services.system_settings import (
    get_testing_timeout_config,
    update_testing_timeout_config,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get(
    "/testing",
    response_model=TestingTimeoutsRead,
    summary="获取快速测试与测试任务的超时时间配置",
)
def get_testing_timeouts(*, db: Session = Depends(get_db)) -> TestingTimeoutsRead:
    config = get_testing_timeout_config(db)
    return TestingTimeoutsRead(
        quick_test_timeout=int(config.quick_test_timeout),
        test_task_timeout=int(config.test_task_timeout),
        updated_at=config.updated_at,
    )


@router.put(
    "/testing",
    response_model=TestingTimeoutsRead,
    summary="更新快速测试与测试任务的超时时间配置",
)
def update_testing_timeouts(
    *,
    db: Session = Depends(get_db),
    payload: TestingTimeoutsUpdate,
) -> TestingTimeoutsRead:
    config = update_testing_timeout_config(
        db,
        quick_test_timeout=payload.quick_test_timeout,
        test_task_timeout=payload.test_task_timeout,
    )
    return TestingTimeoutsRead(
        quick_test_timeout=int(config.quick_test_timeout),
        test_task_timeout=int(config.test_task_timeout),
        updated_at=config.updated_at,
    )


__all__ = ["router"]
