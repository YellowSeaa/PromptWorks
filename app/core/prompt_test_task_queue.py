from __future__ import annotations

import logging
import math
import threading
import time
from datetime import UTC, datetime
from queue import Empty, Queue
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db import session as db_session
from app.models.prompt_test import (
    PromptTestExperiment,
    PromptTestExperimentStatus,
    PromptTestTask,
    PromptTestTaskStatus,
    PromptTestUnit,
)
from app.services.prompt_test_engine import (
    PromptTestExecutionError,
    execute_prompt_test_experiment,
)

logger = logging.getLogger("promptworks.prompt_test_queue")


class PromptTestProgressTracker:
    """在任务执行期间追踪并持久化进度信息。"""

    def __init__(
        self,
        session: Session,
        task: PromptTestTask,
        total_runs: int,
        *,
        step_percent: int = 5,
    ) -> None:
        self._session = session
        self._task = task
        self._configured_total = max(1, int(total_runs)) if total_runs else 1
        self._actual_total = max(1, total_runs)
        self._step = max(1, step_percent)
        self._completed = 0
        self._last_percent = 0
        self._next_threshold = self._step
        self._initialized = False

    def initialize(self) -> None:
        config = dict(self._task.config) if isinstance(self._task.config, dict) else {}
        progress_record = config.get("progress")
        if not isinstance(progress_record, dict):
            progress_record = {}
        progress_record.update(
            {
                "current": 0,
                "total": self._configured_total,
                "percentage": 0,
                "step": self._step,
            }
        )
        config["progress"] = progress_record
        config["progress_current"] = 0
        config["progressCurrent"] = 0
        config["progress_total"] = self._configured_total
        config["progressTotal"] = self._configured_total
        config["progress_percentage"] = 0
        config["progressPercentage"] = 0
        self._task.config = config
        self._initialized = True
        self._session.flush()

    def advance(self, amount: int = 1) -> None:
        if not self._initialized or amount <= 0:
            return
        self._completed = min(self._actual_total, self._completed + amount)
        percent = self._calculate_percent(self._completed)
        if self._completed < self._actual_total and percent < self._next_threshold:
            return
        self._write_progress(self._completed, percent)
        self._last_percent = percent
        if self._completed >= self._actual_total:
            self._next_threshold = 100
        else:
            next_multiple = ((percent // self._step) + 1) * self._step
            self._next_threshold = min(100, max(self._step, next_multiple))
        self._session.commit()

    def finish(self, force: bool = False) -> None:
        if not self._initialized:
            return
        if not force and self._last_percent >= 100:
            return
        self._completed = self._actual_total
        self._write_progress(self._actual_total, 100)
        self._last_percent = 100
        self._session.commit()

    def _calculate_percent(self, completed: int) -> int:
        ratio = completed / self._actual_total if self._actual_total else 0
        percent = math.ceil(ratio * 100)
        return min(100, max(0, percent))

    def _write_progress(self, current: int, percent: int) -> None:
        config = dict(self._task.config) if isinstance(self._task.config, dict) else {}
        progress_record = config.get("progress")
        if not isinstance(progress_record, dict):
            progress_record = {}
        progress_record.update(
            {
                "current": min(current, self._configured_total),
                "total": self._configured_total,
                "percentage": percent,
                "step": self._step,
            }
        )
        config["progress"] = progress_record
        config["progress_current"] = min(current, self._configured_total)
        config["progressCurrent"] = min(current, self._configured_total)
        config["progress_total"] = self._configured_total
        config["progressTotal"] = self._configured_total
        config["progress_percentage"] = percent
        config["progressPercentage"] = percent
        self._task.config = config
        self._session.flush()


def _count_variable_cases(value: Any) -> int:
    if value is None:
        return 1
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return len(value) or 1
    if isinstance(value, Mapping):
        rows = value.get("rows")
        if isinstance(rows, Sequence) and not isinstance(rows, (str, bytes, bytearray)):
            return len(rows) or 1
        length = value.get("length") or value.get("count")
        if isinstance(length, (int, float)) and length > 0:
            return int(length)
        data = value.get("data")
        if isinstance(data, Sequence) and not isinstance(data, (str, bytes, bytearray)):
            return len(data) or 1
    return 1


def _estimate_total_runs(units: Sequence[PromptTestUnit]) -> int:
    total = 0
    for unit in units:
        rounds = unit.rounds or 1
        case_count = _count_variable_cases(unit.variables)
        total += max(1, int(rounds)) * max(1, int(case_count))
    return max(total, 1)


class PromptTestTaskQueue:
    """Prompt 测试任务的串行执行队列。"""

    def __init__(self) -> None:
        self._queue: Queue[int] = Queue()
        self._worker = threading.Thread(
            target=self._worker_loop, name="prompt-test-task-queue", daemon=True
        )
        self._worker.start()

    @staticmethod
    def _update_task_last_error(task: PromptTestTask, message: str | None) -> None:
        if message:
            base = dict(task.config) if isinstance(task.config, dict) else {}
            base["last_error"] = message
            task.config = base
            return

        if isinstance(task.config, dict) and "last_error" in task.config:
            cleaned = dict(task.config)
            cleaned.pop("last_error", None)
            task.config = cleaned

    def enqueue(self, task_id: int) -> None:
        """将任务加入待执行队列。"""

        self._queue.put_nowait(task_id)
        logger.info("Prompt 测试任务 %s 已加入执行队列", task_id)

    def wait_for_idle(self, timeout: float | None = None) -> bool:
        """等待队列清空，便于测试或调试。"""

        if timeout is None:
            self._queue.join()
            return True

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._queue.unfinished_tasks == 0:
                return True
            time.sleep(0.02)
        return self._queue.unfinished_tasks == 0

    def _worker_loop(self) -> None:
        while True:
            try:
                task_id = self._queue.get()
            except Empty:  # pragma: no cover - Queue.get 默认阻塞
                continue

            try:
                self._execute_task(task_id)
            except Exception:  # pragma: no cover - 防御性兜底
                logger.exception(
                    "执行 Prompt 测试任务 %s 过程中发生未捕获异常", task_id
                )
            finally:
                self._queue.task_done()

    def _execute_task(self, task_id: int) -> None:
        session = db_session.SessionLocal()
        try:
            task = session.execute(
                select(PromptTestTask)
                .where(PromptTestTask.id == task_id)
                .options(selectinload(PromptTestTask.units))
            ).scalar_one_or_none()
            if not task:
                logger.warning("Prompt 测试任务 %s 不存在，跳过执行", task_id)
                return
            if task.is_deleted:
                logger.info("Prompt 测试任务 %s 已被标记删除，跳过执行", task_id)
                return

            units = [unit for unit in task.units if isinstance(unit, PromptTestUnit)]
            total_runs = _estimate_total_runs(units)
            progress_tracker = PromptTestProgressTracker(session, task, total_runs)
            progress_tracker.initialize()

            if not units:
                task.status = PromptTestTaskStatus.COMPLETED
                self._update_task_last_error(task, None)
                progress_tracker.finish(force=True)
                logger.info(
                    "Prompt 测试任务 %s 无最小测试单元，自动标记为完成", task_id
                )
                return

            task.status = PromptTestTaskStatus.RUNNING
            self._update_task_last_error(task, None)
            session.commit()

            for unit in units:
                sequence = (
                    session.scalar(
                        select(func.max(PromptTestExperiment.sequence)).where(
                            PromptTestExperiment.unit_id == unit.id
                        )
                    )
                    or 0
                ) + 1

                experiment = PromptTestExperiment(
                    unit_id=unit.id,
                    sequence=sequence,
                    status=PromptTestExperimentStatus.PENDING,
                )
                session.add(experiment)
                session.flush()

                try:
                    execute_prompt_test_experiment(
                        session, experiment, progress_tracker.advance
                    )
                except PromptTestExecutionError as exc:
                    session.refresh(experiment)
                    experiment.status = PromptTestExperimentStatus.FAILED
                    experiment.error = str(exc)
                    experiment.finished_at = datetime.now(UTC)
                    task.status = PromptTestTaskStatus.FAILED
                    self._update_task_last_error(task, str(exc))
                    progress_tracker.finish(force=True)
                    session.commit()
                    logger.warning(
                        "Prompt 测试任务 %s 的最小单元 %s 执行失败: %s",
                        task_id,
                        unit.id,
                        exc,
                    )
                    return
                except Exception as exc:  # pragma: no cover - 防御性兜底
                    session.refresh(experiment)
                    experiment.status = PromptTestExperimentStatus.FAILED
                    experiment.error = "执行测试任务失败"
                    experiment.finished_at = datetime.now(UTC)
                    task.status = PromptTestTaskStatus.FAILED
                    self._update_task_last_error(task, "执行测试任务失败")
                    progress_tracker.finish(force=True)
                    session.commit()
                    logger.exception(
                        "Prompt 测试任务 %s 的最小单元 %s 执行出现未知异常",
                        task_id,
                        unit.id,
                    )
                    return

                session.commit()

            task.status = PromptTestTaskStatus.COMPLETED
            self._update_task_last_error(task, None)
            progress_tracker.finish()
            session.commit()
            logger.info("Prompt 测试任务 %s 执行完成", task_id)
        finally:
            session.close()


task_queue = PromptTestTaskQueue()


def enqueue_prompt_test_task(task_id: int) -> None:
    """对外暴露的入队方法。"""

    task_queue.enqueue(task_id)


__all__ = ["enqueue_prompt_test_task", "task_queue"]
