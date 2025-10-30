from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from app.core.prompt_test_task_queue import enqueue_prompt_test_task, task_queue
from app.models.prompt_test import (
    PromptTestExperiment,
    PromptTestExperimentStatus,
    PromptTestTask,
    PromptTestTaskStatus,
    PromptTestUnit,
)
from app.services.prompt_test_engine import PromptTestExecutionError


@pytest.fixture(autouse=True)
def ensure_queue_idle():
    """在每个用例前后确保队列为空，避免任务相互干扰。"""

    task_queue.wait_for_idle(timeout=2.0)
    yield
    task_queue.wait_for_idle(timeout=2.0)


def test_enqueue_prompt_test_task_handles_missing_task(db_session):
    enqueue_prompt_test_task(999_999)
    task_queue.wait_for_idle(timeout=2.0)
    # 若任务不存在，应当直接返回并保持数据库无额外记录。
    total = db_session.scalar(select(func.count()).select_from(PromptTestExperiment))
    assert total == 0


def test_prompt_test_task_without_units_marks_completed(db_session):
    task = PromptTestTask(
        name="空任务",
        status=PromptTestTaskStatus.READY,
        config={"last_error": "should be cleared"},
    )
    db_session.add(task)
    db_session.commit()

    enqueue_prompt_test_task(task.id)
    task_queue.wait_for_idle(timeout=2.0)

    db_session.expire_all()
    refreshed = db_session.get(PromptTestTask, task.id)
    assert refreshed.status == PromptTestTaskStatus.COMPLETED
    assert refreshed.config and "last_error" not in refreshed.config
    progress = refreshed.config["progress"]
    assert progress["total"] == 1
    assert progress["current"] == 1
    assert progress["percentage"] == 100


def test_prompt_test_task_execution_failure_sets_last_error(db_session, monkeypatch):
    task = PromptTestTask(
        name="失败任务",
        status=PromptTestTaskStatus.READY,
        config=None,
    )
    unit = PromptTestUnit(
        task=task,
        name="单元1",
        model_name="gpt-4o-mini",
        rounds=1,
        temperature=0.5,
    )
    db_session.add_all([task, unit])
    db_session.commit()

    def fail_execute(session, experiment, progress_callback=None):
        raise PromptTestExecutionError("执行失败")

    monkeypatch.setattr(
        "app.core.prompt_test_task_queue.execute_prompt_test_experiment",
        fail_execute,
    )

    enqueue_prompt_test_task(task.id)
    task_queue.wait_for_idle(timeout=2.0)

    db_session.expire_all()
    refreshed = db_session.get(PromptTestTask, task.id)
    assert refreshed.status == PromptTestTaskStatus.FAILED
    assert refreshed.config and refreshed.config.get("last_error") == "执行失败"
    assert refreshed.config["progress"]["percentage"] == 100
    assert (
        refreshed.config["progress"]["current"] == refreshed.config["progress"]["total"]
    )


def test_prompt_test_task_execution_succeeds(db_session, monkeypatch):
    task = PromptTestTask(
        name="成功任务",
        status=PromptTestTaskStatus.READY,
        config={"last_error": "old"},
    )
    unit = PromptTestUnit(
        task=task,
        name="单元成功",
        model_name="gpt-4o-mini",
        rounds=1,
        temperature=0.5,
    )
    db_session.add_all([task, unit])
    db_session.commit()

    def succeed_execute(session, experiment, progress_callback=None):
        if progress_callback:
            progress_callback(1)
        experiment.status = PromptTestExperimentStatus.COMPLETED
        experiment.finished_at = datetime.now(UTC)
        session.flush()

    monkeypatch.setattr(
        "app.core.prompt_test_task_queue.execute_prompt_test_experiment",
        succeed_execute,
    )

    enqueue_prompt_test_task(task.id)
    task_queue.wait_for_idle(timeout=2.0)

    db_session.expire_all()
    refreshed = db_session.get(PromptTestTask, task.id)
    assert refreshed.status == PromptTestTaskStatus.COMPLETED
    assert refreshed.config and "last_error" not in refreshed.config
    progress = refreshed.config["progress"]
    assert progress["total"] == 1
    assert progress["current"] == 1
    assert progress["percentage"] == 100

    experiments = db_session.scalars(
        select(PromptTestExperiment).where(PromptTestExperiment.unit_id == unit.id)
    ).all()
    assert experiments and experiments[0].status == PromptTestExperimentStatus.COMPLETED


def test_prompt_test_task_progress_tracks_total_runs(db_session, monkeypatch):
    task = PromptTestTask(
        name="进度统计任务",
        status=PromptTestTaskStatus.READY,
        config=None,
    )
    unit = PromptTestUnit(
        task=task,
        name="含变量单元",
        model_name="gpt-4o-mini",
        rounds=2,
        temperature=0.5,
        variables={"rows": [{"text": "A"}, {"text": "B"}, {"text": "C"}]},
    )
    db_session.add_all([task, unit])
    db_session.commit()

    expected_total = 6

    def execute_with_progress(session, experiment, progress_callback=None):
        if progress_callback:
            for _ in range(expected_total):
                progress_callback(1)
        experiment.status = PromptTestExperimentStatus.COMPLETED
        experiment.finished_at = datetime.now(UTC)
        session.flush()

    monkeypatch.setattr(
        "app.core.prompt_test_task_queue.execute_prompt_test_experiment",
        execute_with_progress,
    )

    enqueue_prompt_test_task(task.id)
    task_queue.wait_for_idle(timeout=2.0)

    db_session.expire_all()
    refreshed = db_session.get(PromptTestTask, task.id)
    assert refreshed.status == PromptTestTaskStatus.COMPLETED
    progress = refreshed.config["progress"]
    assert progress["total"] == expected_total
    assert progress["current"] == expected_total
    assert progress["percentage"] == 100
