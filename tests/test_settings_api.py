from __future__ import annotations

from datetime import datetime

from app.models.system_setting import SystemSetting


def test_get_testing_timeouts_returns_defaults(client):
    response = client.get("/api/v1/settings/testing")
    assert response.status_code == 200
    data = response.json()
    assert data["quick_test_timeout"] == 30
    assert data["test_task_timeout"] == 30
    assert data["updated_at"] is None


def test_update_testing_timeouts(client, db_session):
    response = client.put(
        "/api/v1/settings/testing",
        json={"quick_test_timeout": 40, "test_task_timeout": 150},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["quick_test_timeout"] == 40
    assert data["test_task_timeout"] == 150
    assert isinstance(data["updated_at"], str)

    record = db_session.get(SystemSetting, "testing_timeout")
    assert record is not None
    assert record.value == {
        "quick_test_timeout": 40.0,
        "test_task_timeout": 150.0,
    }
    assert isinstance(record.updated_at, datetime)
