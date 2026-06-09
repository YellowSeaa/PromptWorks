from __future__ import annotations

from datetime import datetime

import pytest

from app.models.system_setting import SystemSetting
from app.services.system_settings import (
    DEFAULT_AI_OPTIMIZATION_TIMEOUT,
    DEFAULT_QUICK_TEST_TIMEOUT,
    DEFAULT_TEST_TASK_TIMEOUT,
    get_testing_timeout_config,
    update_testing_timeout_config,
)


def test_get_testing_timeout_config_returns_defaults(db_session):
    config = get_testing_timeout_config(db_session)
    assert config.quick_test_timeout == DEFAULT_QUICK_TEST_TIMEOUT
    assert config.test_task_timeout == DEFAULT_TEST_TASK_TIMEOUT
    assert config.ai_optimization_timeout == DEFAULT_AI_OPTIMIZATION_TIMEOUT
    assert config.updated_at is None


def test_update_testing_timeout_config_persists_values(db_session):
    config = update_testing_timeout_config(
        db_session,
        quick_test_timeout=45,
        test_task_timeout=180,
        ai_optimization_timeout=240,
    )
    assert config.quick_test_timeout == 45
    assert config.test_task_timeout == 180
    assert config.ai_optimization_timeout == 240
    assert isinstance(config.updated_at, datetime)

    refreshed = get_testing_timeout_config(db_session)
    assert refreshed.quick_test_timeout == 45
    assert refreshed.test_task_timeout == 180
    assert refreshed.ai_optimization_timeout == 240


@pytest.mark.parametrize(
    "payload",
    [
        {
            "quick_test_timeout": 0,
            "test_task_timeout": 10,
            "ai_optimization_timeout": 60,
            "expected_task": 10.0,
            "expected_ai": 60.0,
        },
        {
            "quick_test_timeout": -5,
            "test_task_timeout": "abc",
            "ai_optimization_timeout": "bad",
            "expected_task": DEFAULT_TEST_TASK_TIMEOUT,
            "expected_ai": DEFAULT_AI_OPTIMIZATION_TIMEOUT,
        },
    ],
)
def test_update_testing_timeout_config_invalid_values_use_defaults(db_session, payload):
    update_testing_timeout_config(
        db_session,
        quick_test_timeout=payload["quick_test_timeout"],
        test_task_timeout=payload["test_task_timeout"],
        ai_optimization_timeout=payload["ai_optimization_timeout"],
    )
    record = db_session.get(SystemSetting, "testing_timeout")
    assert record is not None
    assert record.value["quick_test_timeout"] == DEFAULT_QUICK_TEST_TIMEOUT
    assert record.value["test_task_timeout"] == payload["expected_task"]
    assert record.value["ai_optimization_timeout"] == payload["expected_ai"]
