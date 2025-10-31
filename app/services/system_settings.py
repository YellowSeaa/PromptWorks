from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.system_setting import SystemSetting

TESTING_TIMEOUT_SETTING_KEY = "testing_timeout"
DEFAULT_QUICK_TEST_TIMEOUT = 30.0
DEFAULT_TEST_TASK_TIMEOUT = 30.0


@dataclass(slots=True)
class TestingTimeoutConfig:
    """封装快速测试与测试任务的超时配置。"""

    quick_test_timeout: float
    test_task_timeout: float
    updated_at: datetime | None = None


def _coerce_timeout(value: Any, default: float) -> float:
    """将任意输入转换为合法的超时秒数。"""

    numeric: float | None = None
    if isinstance(value, (int, float)):
        numeric = float(value)
    elif isinstance(value, str):
        try:
            numeric = float(value.strip())
        except ValueError:
            numeric = None

    if numeric is None or not numeric > 0:
        return default
    return float(numeric)


def get_testing_timeout_config(db: Session) -> TestingTimeoutConfig:
    """读取快速测试与测试任务的超时配置，若未设置则返回默认值。"""

    record = db.get(SystemSetting, TESTING_TIMEOUT_SETTING_KEY)
    if record is None:
        return TestingTimeoutConfig(
            quick_test_timeout=DEFAULT_QUICK_TEST_TIMEOUT,
            test_task_timeout=DEFAULT_TEST_TASK_TIMEOUT,
            updated_at=None,
        )

    value = record.value if isinstance(record.value, Mapping) else {}
    quick_timeout = _coerce_timeout(
        value.get("quick_test_timeout", DEFAULT_QUICK_TEST_TIMEOUT),
        DEFAULT_QUICK_TEST_TIMEOUT,
    )
    task_timeout = _coerce_timeout(
        value.get("test_task_timeout", DEFAULT_TEST_TASK_TIMEOUT),
        DEFAULT_TEST_TASK_TIMEOUT,
    )
    return TestingTimeoutConfig(
        quick_test_timeout=quick_timeout,
        test_task_timeout=task_timeout,
        updated_at=record.updated_at,
    )


def update_testing_timeout_config(
    db: Session,
    *,
    quick_test_timeout: float,
    test_task_timeout: float,
) -> TestingTimeoutConfig:
    """更新快速测试与测试任务的超时配置。"""

    sanitized_quick = _coerce_timeout(quick_test_timeout, DEFAULT_QUICK_TEST_TIMEOUT)
    sanitized_task = _coerce_timeout(test_task_timeout, DEFAULT_TEST_TASK_TIMEOUT)
    payload = {
        "quick_test_timeout": sanitized_quick,
        "test_task_timeout": sanitized_task,
    }

    record = db.get(SystemSetting, TESTING_TIMEOUT_SETTING_KEY)
    if record is None:
        record = SystemSetting(
            key=TESTING_TIMEOUT_SETTING_KEY,
            value=payload,
            description="快速测试与测试任务的超时时间（秒）",
        )
        db.add(record)
    else:
        record.value = payload

    db.flush()
    db.commit()
    db.refresh(record)

    return TestingTimeoutConfig(
        quick_test_timeout=sanitized_quick,
        test_task_timeout=sanitized_task,
        updated_at=record.updated_at,
    )


__all__ = [
    "TestingTimeoutConfig",
    "DEFAULT_QUICK_TEST_TIMEOUT",
    "DEFAULT_TEST_TASK_TIMEOUT",
    "get_testing_timeout_config",
    "update_testing_timeout_config",
]
