from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import func, select

from app.core import prompt_test_task_queue
from app.models.llm_provider import LLMModel, LLMProvider
from app.models.prompt import Prompt, PromptClass, PromptVersion
from app.models.prompt_test import (
    PromptTestExperiment,
    PromptTestExperimentStatus,
    PromptTestTask,
    PromptTestTaskStatus,
    PromptTestUnit,
)
from app.models.system_setting import SystemSetting
from app.models.usage import LLMUsageLog
from app.services import prompt_test_engine
from app.services.prompt_test_engine import execute_prompt_test_experiment
from app.services.system_settings import DEFAULT_TEST_TASK_TIMEOUT


class DummyResponse:
    """用于伪造 httpx 返回值的简单封装。"""

    def __init__(self, payload: dict[str, Any], *, elapsed_ms: int | None) -> None:
        self._payload = payload
        self.status_code = 200
        self.elapsed = (
            timedelta(milliseconds=elapsed_ms) if elapsed_ms is not None else None
        )

    def json(self) -> dict[str, Any]:
        return self._payload

    @property
    def text(self) -> str:
        return ""


def _create_prompt_version(db_session) -> PromptVersion:
    prompt_class = PromptClass(name="测试类")
    prompt = Prompt(name="翻译测试", prompt_class=prompt_class)
    version = PromptVersion(
        prompt=prompt, version="v1", content="你是一位严谨的翻译助手。"
    )
    prompt.current_version = version
    db_session.add_all([prompt_class, prompt, version])
    db_session.commit()
    return version


def _create_provider_and_model(
    db_session, *, base_url: str | None = "https://llm.fake/api"
) -> LLMModel:
    provider = LLMProvider(
        provider_name="Internal",
        provider_key=None,
        api_key="fake-key",
        is_custom=True,
        base_url=base_url,
    )
    model = LLMModel(provider=provider, name="chat-mini")
    db_session.add_all([provider, model])
    db_session.commit()
    return model


def test_prompt_test_engine_build_messages_snapshot_uses_user_role():
    unit = PromptTestUnit(
        task_id=1,
        prompt_version_id=None,
        name="快照测试",
        model_name="mock-model",
        rounds=1,
        prompt_template="第 {run_index} 次提问",
    )
    context = {"run_index": 1}
    messages = prompt_test_engine._build_messages(
        unit, "你是一位审校专家。", context, run_index=1
    )
    assert len(messages) >= 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "你是一位审校专家。"
    assert messages[1]["role"] == "user"
    assert "第 1 次提问" in messages[1]["content"]


def test_execute_prompt_test_experiment_generates_metrics(db_session, monkeypatch):
    prompt_version = _create_prompt_version(db_session)
    model = _create_provider_and_model(db_session)
    provider = model.provider
    before_count = db_session.scalar(select(func.count()).select_from(LLMUsageLog)) or 0

    task = PromptTestTask(name="多轮翻译基准", prompt_version_id=prompt_version.id)
    unit = PromptTestUnit(
        task=task,
        prompt_version_id=prompt_version.id,
        name="翻译成英语",
        model_name=model.name,
        llm_provider_id=provider.id,
        rounds=2,
        prompt_template="请翻译：{text}",
        variables={"cases": [{"text": "你好"}, {"text": "谢谢"}]},
        parameters={"max_tokens": 32},
    )
    experiment = PromptTestExperiment(unit=unit, sequence=1)

    db_session.add_all([task, unit, experiment])
    db_session.commit()

    def fake_post(*_, **kwargs):
        payload = kwargs.get("json") or {}
        assert kwargs["timeout"] == DEFAULT_TEST_TASK_TIMEOUT
        messages = payload.get("messages") or []
        user_text = messages[-1]["content"] if messages else ""
        if "你好" in user_text:
            response = {
                "choices": [{"message": {"content": "Hello"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 4},
            }
            return DummyResponse(response, elapsed_ms=18)
        response = {
            "choices": [{"message": {"content": '{"value":"Thanks"}'}}],
            "usage": {"total_tokens": 16},
        }
        return DummyResponse(response, elapsed_ms=24)

    monkeypatch.setattr("app.services.prompt_test_engine.httpx.post", fake_post)

    execute_prompt_test_experiment(db_session, experiment)
    db_session.commit()

    refreshed = db_session.get(PromptTestExperiment, experiment.id)
    assert refreshed.status == PromptTestExperimentStatus.COMPLETED
    assert refreshed.outputs is not None and len(refreshed.outputs) == 4
    assert refreshed.outputs[0]["output_text"] == "Hello"
    assert refreshed.outputs[1]["parsed_output"] == {"value": "Thanks"}
    assert refreshed.outputs[2]["output_text"] == "Hello"
    assert refreshed.outputs[3]["parsed_output"] == {"value": "Thanks"}
    assert [item["variables"] for item in refreshed.outputs] == [
        {"text": "你好"},
        {"text": "谢谢"},
        {"text": "你好"},
        {"text": "谢谢"},
    ]

    metrics = refreshed.metrics
    assert metrics and metrics["rounds"] == 4
    assert metrics["json_success_rate"] == pytest.approx(0.5, rel=1e-3)
    assert metrics["avg_latency_ms"] > 0
    after_count = db_session.scalar(select(func.count()).select_from(LLMUsageLog)) or 0
    assert after_count - before_count == 4

    recent_logs = db_session.scalars(
        select(LLMUsageLog)
        .where(
            LLMUsageLog.source == "prompt_test",
            LLMUsageLog.prompt_version_id == prompt_version.id,
        )
        .order_by(LLMUsageLog.id.desc())
    ).all()
    assert len(recent_logs) >= 4
    latest_log = recent_logs[0]
    assert latest_log.model_name == model.name
    assert latest_log.prompt_tokens is not None or latest_log.total_tokens is not None


def test_prompt_test_engine_uses_custom_timeout(db_session, monkeypatch):
    prompt_version = _create_prompt_version(db_session)
    model = _create_provider_and_model(db_session)
    provider = model.provider

    custom_timeout = 90
    db_session.add(
        SystemSetting(
            key="testing_timeout",
            value={"quick_test_timeout": 45, "test_task_timeout": custom_timeout},
        )
    )
    db_session.commit()

    task = PromptTestTask(name="自定义超时任务", prompt_version_id=prompt_version.id)
    unit = PromptTestUnit(
        task=task,
        prompt_version_id=prompt_version.id,
        name="翻译单句",
        model_name=model.name,
        llm_provider_id=provider.id,
        rounds=1,
        prompt_template="翻译：{text}",
        variables={"cases": [{"text": "你好"}]},
        parameters={"max_tokens": 8},
    )
    experiment = PromptTestExperiment(unit=unit, sequence=1)

    db_session.add_all([task, unit, experiment])
    db_session.commit()

    def fake_post(*_, **kwargs):
        assert kwargs["timeout"] == custom_timeout
        response = {
            "choices": [{"message": {"content": "Hello"}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 4},
        }
        return DummyResponse(response, elapsed_ms=12)

    monkeypatch.setattr("app.services.prompt_test_engine.httpx.post", fake_post)

    execute_prompt_test_experiment(db_session, experiment)

    refreshed = db_session.get(PromptTestExperiment, experiment.id)
    assert refreshed is not None
    assert refreshed.status == PromptTestExperimentStatus.COMPLETED


def test_prompt_test_api_creates_and_executes_experiment(
    client, db_session, monkeypatch
):
    prompt_version = _create_prompt_version(db_session)
    model = _create_provider_and_model(db_session)
    provider = model.provider

    def fake_post(*_, **kwargs):
        assert kwargs["timeout"] == DEFAULT_TEST_TASK_TIMEOUT
        response = {
            "choices": [{"message": {"content": "Hello World"}}],
            "usage": {"prompt_tokens": 4, "completion_tokens": 5},
        }
        return DummyResponse(response, elapsed_ms=10)

    monkeypatch.setattr("app.services.prompt_test_engine.httpx.post", fake_post)

    response = client.post(
        "/api/v1/prompt-test/tasks",
        json={
            "name": "集成实验",
            "prompt_version_id": prompt_version.id,
            "units": [
                {
                    "name": "翻译单元",
                    "model_name": model.name,
                    "llm_provider_id": provider.id,
                    "rounds": 1,
                    "prompt_template": "翻译：{text}",
                    "variables": {"text": "你好"},
                    "parameters": {"max_tokens": 16},
                }
            ],
        },
    )
    assert response.status_code == 201
    task_id = response.json()["id"]

    unit_resp = client.get(f"/api/v1/prompt-test/tasks/{task_id}/units")
    assert unit_resp.status_code == 200
    unit_list = unit_resp.json()
    assert len(unit_list) == 1
    unit_id = unit_list[0]["id"]

    experiment_resp = client.post(
        f"/api/v1/prompt-test/units/{unit_id}/experiments",
        json={"auto_execute": True, "batch_id": "batch-1"},
    )
    assert experiment_resp.status_code == 201
    body = experiment_resp.json()
    assert body["status"] == PromptTestExperimentStatus.COMPLETED.value
    assert body["metrics"]["rounds"] == 1
    assert body["outputs"][0]["output_text"] == "Hello World"
    assert body["outputs"][0]["variables"] == {"text": "你好"}

    detail_resp = client.get(f"/api/v1/prompt-test/experiments/{body['id']}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["status"] == PromptTestExperimentStatus.COMPLETED.value


def test_execute_prompt_test_experiment_continues_after_run_failure(
    db_session, monkeypatch
):
    prompt_version = _create_prompt_version(db_session)
    model = _create_provider_and_model(db_session)

    task = PromptTestTask(name="允许部分失败", prompt_version_id=prompt_version.id)
    unit = PromptTestUnit(
        task=task,
        prompt_version_id=prompt_version.id,
        name="重试单元",
        model_name=model.name,
        llm_provider_id=model.provider_id,
        rounds=2,
        parameters={"max_tokens": 16},
    )
    experiment = PromptTestExperiment(unit=unit, sequence=1)

    db_session.add_all([task, unit, experiment])
    db_session.commit()

    def fake_single_round(
        *,
        provider,
        model,
        unit,
        prompt_snapshot,
        base_parameters,
        context,
        run_index,
        request_timeout,
    ):
        if run_index == 1:
            raise prompt_test_engine.PromptTestExecutionError(
                "LLM 网络错误", status_code=502
            )
        return {
            "run_index": run_index,
            "messages": [],
            "parameters": base_parameters,
            "variables": context,
            "output_text": f"结果 {run_index}",
            "parsed_output": None,
            "prompt_tokens": 4,
            "completion_tokens": 4,
            "total_tokens": 8,
            "latency_ms": 15,
            "raw_response": {"choices": []},
        }

    monkeypatch.setattr(
        "app.services.prompt_test_engine._execute_single_round", fake_single_round
    )

    execute_prompt_test_experiment(db_session, experiment)

    refreshed = db_session.get(PromptTestExperiment, experiment.id)
    assert refreshed is not None
    assert refreshed.status == PromptTestExperimentStatus.COMPLETED
    assert refreshed.error and "1 次调用失败" in refreshed.error
    assert len(refreshed.outputs or []) == 2
    assert refreshed.outputs[0]["error"] == "LLM 网络错误"
    assert refreshed.outputs[1]["output_text"] == "结果 2"
    assert refreshed.metrics["failed_runs"] == 1


def test_prompt_test_task_queue_executes_task_and_persists_results(
    client, db_session, monkeypatch
):
    prompt_version = _create_prompt_version(db_session)
    model = _create_provider_and_model(db_session)
    provider = model.provider

    def fake_post(*_, **kwargs):
        payload = kwargs.get("json") or {}
        messages = payload.get("messages") or []
        user_text = messages[-1]["content"] if messages else ""
        if "你好" in user_text:
            response = {
                "choices": [{"message": {"content": "Hello"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 4},
            }
        else:
            response = {
                "choices": [{"message": {"content": "World"}}],
                "usage": {"total_tokens": 16},
            }
        return DummyResponse(response, elapsed_ms=18)

    monkeypatch.setattr("app.services.prompt_test_engine.httpx.post", fake_post)

    response = client.post(
        "/api/v1/prompt-test/tasks",
        json={
            "name": "队列执行验证",
            "prompt_version_id": prompt_version.id,
            "auto_execute": True,
            "units": [
                {
                    "name": "翻译单元",
                    "model_name": model.name,
                    "llm_provider_id": provider.id,
                    "rounds": 2,
                    "prompt_template": "翻译：{text}",
                    "variables": {"cases": [{"text": "你好"}, {"text": "谢谢"}]},
                    "parameters": {"max_tokens": 16},
                }
            ],
        },
    )
    assert response.status_code == 201
    task = response.json()
    task_id = task["id"]

    units_resp = client.get(f"/api/v1/prompt-test/tasks/{task_id}/units")
    assert units_resp.status_code == 200
    units_data = units_resp.json()
    assert len(units_data) == 1
    unit_id = units_data[0]["id"]

    from app.core import prompt_test_task_queue

    assert prompt_test_task_queue.task_queue.wait_for_idle(timeout=2.0)

    experiments_resp = client.get(f"/api/v1/prompt-test/units/{unit_id}/experiments")
    assert experiments_resp.status_code == 200
    experiments = experiments_resp.json()
    assert experiments, "队列执行后应至少生成一个实验记录"
    latest = experiments[0]
    assert latest["status"] == PromptTestExperimentStatus.COMPLETED.value
    assert latest["outputs"], "实验记录应包含输出结果"


def test_soft_delete_prompt_test_task_hides_from_list(client, db_session):
    prompt_version = _create_prompt_version(db_session)
    model = _create_provider_and_model(db_session)
    provider = model.provider

    response = client.post(
        "/api/v1/prompt-test/tasks",
        json={
            "name": "软删任务",
            "prompt_version_id": prompt_version.id,
            "units": [
                {
                    "name": "基础单元",
                    "model_name": model.name,
                    "llm_provider_id": provider.id,
                    "rounds": 1,
                    "prompt_template": "示例：{text}",
                    "variables": {"text": "测试"},
                }
            ],
        },
    )
    assert response.status_code == 201
    task_id = response.json()["id"]

    delete_resp = client.delete(f"/api/v1/prompt-test/tasks/{task_id}")
    assert delete_resp.status_code == 204

    db_session.expire_all()
    task = db_session.get(PromptTestTask, task_id)
    assert task is not None and task.is_deleted

    list_resp = client.get("/api/v1/prompt-test/tasks")
    task_ids = [item["id"] for item in list_resp.json()]
    assert task_id not in task_ids

    detail_resp = client.get(f"/api/v1/prompt-test/tasks/{task_id}")
    assert detail_resp.status_code == 404

    units_resp = client.get(f"/api/v1/prompt-test/tasks/{task_id}/units")
    assert units_resp.status_code == 404

    delete_again = client.delete(f"/api/v1/prompt-test/tasks/{task_id}")
    assert delete_again.status_code == 404


def test_list_prompt_test_tasks_supports_status_filter(client, db_session):
    prompt_version = _create_prompt_version(db_session)
    ready_task = PromptTestTask(
        name="已就绪任务",
        prompt_version_id=prompt_version.id,
        status=PromptTestTaskStatus.READY,
    )
    draft_task = PromptTestTask(
        name="草稿任务",
        prompt_version_id=prompt_version.id,
        status=PromptTestTaskStatus.DRAFT,
    )
    db_session.add_all([ready_task, draft_task])
    db_session.commit()

    resp = client.get(
        "/api/v1/prompt-test/tasks", params={"status": PromptTestTaskStatus.READY.value}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["name"] == "已就绪任务"
    assert body[0]["status"] == PromptTestTaskStatus.READY.value


def test_prompt_test_task_crud_and_unit_management(client, db_session):
    prompt_version = _create_prompt_version(db_session)
    model = _create_provider_and_model(db_session)
    provider = model.provider

    create_resp = client.post(
        "/api/v1/prompt-test/tasks",
        json={"name": "任务管理", "prompt_version_id": prompt_version.id},
    )
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    detail_resp = client.get(f"/api/v1/prompt-test/tasks/{task_id}")
    assert detail_resp.status_code == 200

    patch_resp = client.patch(
        f"/api/v1/prompt-test/tasks/{task_id}",
        json={
            "description": "更新描述",
            "status": PromptTestTaskStatus.RUNNING.value,
        },
    )
    assert patch_resp.status_code == 200
    updated_task = patch_resp.json()
    assert updated_task["description"] == "更新描述"
    assert updated_task["status"] == PromptTestTaskStatus.RUNNING.value

    unit_payload = {
        "name": "新增单元",
        "model_name": model.name,
        "llm_provider_id": provider.id,
        "prompt_version_id": prompt_version.id,
        "rounds": 2,
        "prompt_template": "示例：{text}",
        "variables": {"text": "世界"},
        "temperature": 0.5,
    }
    unit_resp = client.post(
        f"/api/v1/prompt-test/tasks/{task_id}/units", json=unit_payload
    )
    assert unit_resp.status_code == 201
    unit_id = unit_resp.json()["id"]

    unit_detail = client.get(f"/api/v1/prompt-test/units/{unit_id}")
    assert unit_detail.status_code == 200
    assert unit_detail.json()["name"] == "新增单元"

    unit_update = client.patch(
        f"/api/v1/prompt-test/units/{unit_id}",
        json={"description": "重新描述", "temperature": 0.4},
    )
    assert unit_update.status_code == 200
    assert unit_update.json()["description"] == "重新描述"
    assert unit_update.json()["temperature"] == 0.4


def test_get_prompt_test_unit_rejects_deleted_task(client, db_session):
    prompt_version = _create_prompt_version(db_session)
    model = _create_provider_and_model(db_session)
    task = PromptTestTask(name="软删单元", prompt_version_id=prompt_version.id)
    unit = PromptTestUnit(
        task=task,
        prompt_version_id=prompt_version.id,
        name="无效单元",
        model_name=model.name,
        llm_provider_id=model.provider_id,
        rounds=1,
    )
    db_session.add_all([task, unit])
    db_session.commit()

    task.is_deleted = True
    db_session.commit()

    resp = client.get(f"/api/v1/prompt-test/units/{unit.id}")
    assert resp.status_code == 404


def test_create_experiment_auto_execute_failure_records_error(
    client, db_session, monkeypatch
):
    prompt_version = _create_prompt_version(db_session)
    model = _create_provider_and_model(db_session)
    task = PromptTestTask(name="自动执行失败", prompt_version_id=prompt_version.id)
    unit = PromptTestUnit(
        task=task,
        prompt_version_id=prompt_version.id,
        name="失败单元",
        model_name=model.name,
        llm_provider_id=model.provider_id,
        rounds=1,
    )
    db_session.add_all([task, unit])
    db_session.commit()

    def fake_execute(db, experiment):
        raise prompt_test_engine.PromptTestExecutionError("LLM 超时")

    monkeypatch.setattr(
        "app.api.v1.endpoints.prompt_test_tasks.execute_prompt_test_experiment",
        fake_execute,
    )

    resp = client.post(
        f"/api/v1/prompt-test/units/{unit.id}/experiments", json={"auto_execute": True}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == PromptTestExperimentStatus.FAILED.value
    assert "超时" in body["error"]
    assert body["finished_at"] is not None


def test_get_prompt_test_experiment_handles_missing_and_deleted(client, db_session):
    missing_resp = client.get("/api/v1/prompt-test/experiments/999999")
    assert missing_resp.status_code == 404

    prompt_version = _create_prompt_version(db_session)
    model = _create_provider_and_model(db_session)
    task = PromptTestTask(name="删除实验任务", prompt_version_id=prompt_version.id)
    unit = PromptTestUnit(
        task=task,
        prompt_version_id=prompt_version.id,
        name="实验单元",
        model_name=model.name,
        llm_provider_id=model.provider_id,
        rounds=1,
    )
    experiment = PromptTestExperiment(unit=unit, sequence=1)
    db_session.add_all([task, unit, experiment])
    db_session.commit()

    task.is_deleted = True
    db_session.commit()

    resp = client.get(f"/api/v1/prompt-test/experiments/{experiment.id}")
    assert resp.status_code == 404


def test_execute_existing_experiment_handles_engine_error(
    client, db_session, monkeypatch
):
    prompt_version = _create_prompt_version(db_session)
    model = _create_provider_and_model(db_session)
    task = PromptTestTask(name="重新执行任务", prompt_version_id=prompt_version.id)
    unit = PromptTestUnit(
        task=task,
        prompt_version_id=prompt_version.id,
        name="需要重跑的单元",
        model_name=model.name,
        llm_provider_id=model.provider_id,
        rounds=1,
    )
    experiment = PromptTestExperiment(unit=unit, sequence=1)
    db_session.add_all([task, unit, experiment])
    db_session.commit()

    def fake_execute(db, experiment):
        raise prompt_test_engine.PromptTestExecutionError("二次执行失败")

    monkeypatch.setattr(
        "app.api.v1.endpoints.prompt_test_tasks.execute_prompt_test_experiment",
        fake_execute,
    )

    resp = client.post(f"/api/v1/prompt-test/experiments/{experiment.id}/execute")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == PromptTestExperimentStatus.FAILED.value
    assert "二次执行失败" in body["error"]
    assert body["finished_at"] is not None
