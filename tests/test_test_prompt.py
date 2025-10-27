from __future__ import annotations

from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.task_queue import task_queue
from app.models.result import Result
from app.models.usage import LLMUsageLog
from app.services.test_run import TestRunExecutionError


def _create_prompt(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/prompts/",
        json={
            "name": "对话助手",
            "version": "v1",
            "content": "你是一位擅长助人的智能助手。",
            "class_name": "聊天类",
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_provider_with_model(
    client: TestClient,
) -> tuple[dict[str, Any], dict[str, Any]]:
    provider_resp = client.post(
        "/api/v1/llm-providers/",
        json={
            "provider_name": "Internal",
            "api_key": "test-secret",
            "is_custom": True,
            "base_url": "https://llm.internal/api",
            "logo_emoji": "🤖",
        },
    )
    assert provider_resp.status_code == 201
    provider = provider_resp.json()

    model_resp = client.post(
        f"/api/v1/llm-providers/{provider['id']}/models",
        json={"name": "chat-mini", "capability": "测试"},
    )
    assert model_resp.status_code == 201
    model = model_resp.json()
    assert model["name"] == "chat-mini"
    return provider, model


def test_create_test_prompt_requires_prompt_version(client: TestClient) -> None:
    """缺少有效 Prompt 版本时创建测试任务返回 404。"""
    response = client.post(
        "/api/v1/test_prompt/",
        json={
            "prompt_version_id": 999,
            "model_name": "gpt-4o",
            "temperature": 0.1,
            "top_p": 0.9,
            "repetitions": 1,
        },
    )
    assert response.status_code == 404


def test_create_and_retrieve_test_prompt(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    """验证测试任务创建后可通过列表和详情接口读取。"""

    provider, model = _create_provider_with_model(client)

    invocation_records: list[dict[str, Any]] = []

    def fake_invoke(
        *,
        provider,
        model,
        base_url,
        headers,
        payload,
        context,
    ):
        invocation_records.append(
            {
                "url": f"{base_url}/chat/completions",
                "headers": headers,
                "payload": payload,
                "timeout": 30.0,
            }
        )
        messages = payload.get("messages") if isinstance(payload, dict) else []
        user_content = ""
        if isinstance(messages, list) and len(messages) > 1:
            candidate = messages[1]
            if isinstance(candidate, dict):
                user_content = str(candidate.get("content", ""))
        run_index = 1 if "第一" in user_content else 2
        result = Result(
            output=f"第 {run_index} 次响应内容",
            parsed_output=None,
            tokens_used=120 + run_index,
            latency_ms=150 + run_index,
        )
        param_dict = {
            key: value
            for key, value in payload.items()
            if key not in {"model", "messages"}
        }
        usage_log = LLMUsageLog(
            provider_id=provider.id,
            model_id=model.id if model else None,
            model_name=model.name if model else payload.get("model"),
            source="test_run",
            prompt_id=context.prompt_id,
            prompt_version_id=context.prompt_version_id,
            messages=payload.get("messages"),
            parameters=param_dict or None,
            response_text=result.output,
            temperature=param_dict.get("temperature") if param_dict else None,
            latency_ms=result.latency_ms,
            prompt_tokens=100 + run_index,
            completion_tokens=20 + run_index,
            total_tokens=120 + run_index,
        )
        return result, usage_log

    monkeypatch.setattr("app.services.test_run._invoke_llm_once", fake_invoke)

    prompt_payload = _create_prompt(client)
    prompt_version_id = prompt_payload["current_version"]["id"]

    create_resp = client.post(
        "/api/v1/test_prompt/",
        json={
            "prompt_version_id": prompt_version_id,
            "model_name": model["name"],
            "model_version": provider["provider_name"],
            "temperature": 0.2,
            "top_p": 0.95,
            "repetitions": 2,
            "notes": "示例测试",
            "schema": {
                "inputs": ["第一轮提问", "第二轮提问"],
                "llm_parameters": {"max_tokens": 64},
                "job_name": "示例 A/B 测试",
            },
        },
    )
    assert create_resp.status_code == 201
    test_prompt = create_resp.json()
    initial_status = test_prompt["status"]
    assert initial_status in {"pending", "running", "completed"}
    if initial_status != "completed":
        assert test_prompt["results"] == []
    assert test_prompt["prompt_version_id"] == prompt_version_id
    assert test_prompt["prompt_version"]["version"] == "v1"
    assert test_prompt["prompt"]["name"] == prompt_payload["name"]

    assert len(invocation_records) == 2
    seen_prompts: set[str] = set()
    for record in invocation_records:
        assert record["url"].endswith("/chat/completions")
        assert record["headers"]["Authorization"].startswith("Bearer test-secret")
        payload = record["payload"]
        assert payload["model"] == model["name"]
        assert payload["max_tokens"] == 64
        assert payload["temperature"] == 0.2
        assert payload["messages"][0]["role"] == "user"
        assert (
            payload["messages"][0]["content"]
            == prompt_payload["current_version"]["content"]
        )
        user_content = payload["messages"][1]["content"]
        assert user_content in {"第一轮提问", "第二轮提问"}
        seen_prompts.add(user_content)

    assert seen_prompts == {"第一轮提问", "第二轮提问"}

    assert task_queue.wait_for_idle(timeout=2.0)

    list_resp = client.get("/api/v1/test_prompt/")
    assert list_resp.status_code == 200
    results = list_resp.json()
    assert len(results) == 1
    assert results[0]["id"] == test_prompt["id"]
    assert results[0]["status"] == "completed"
    assert results[0]["failure_reason"] is None

    detail_resp = client.get(f"/api/v1/test_prompt/{test_prompt['id']}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["status"] == "completed"
    assert detail["failure_reason"] is None
    assert detail["prompt_version"]["id"] == prompt_version_id
    assert detail["prompt"]["id"] == prompt_payload["id"]
    assert len(detail["results"]) == 2
    assert (
        detail["schema"]["prompt_snapshot"]
        == prompt_payload["current_version"]["content"]
    )

    sorted_results = sorted(detail["results"], key=lambda item: item["run_index"])
    assert sorted_results[0]["run_index"] == 1
    assert sorted_results[0]["tokens_used"] == 121
    assert sorted_results[0]["latency_ms"] == 151
    assert sorted_results[1]["run_index"] == 2
    assert sorted_results[1]["tokens_used"] == 122
    assert sorted_results[1]["latency_ms"] == 152

    list_results_resp = client.get(f"/api/v1/test_prompt/{test_prompt['id']}/results")
    assert list_results_resp.status_code == 200
    results_payload = list_results_resp.json()
    assert len(results_payload) == 2
    assert {item["run_index"] for item in results_payload} == {1, 2}

    usage_logs = list(
        db_session.scalars(
            select(LLMUsageLog).where(
                LLMUsageLog.prompt_version_id == prompt_version_id,
                LLMUsageLog.source == "test_run",
            )
        )
    )
    assert len(usage_logs) == 2
    assert all(log.source == "test_run" for log in usage_logs)
    assert all(log.model_name == model["name"] for log in usage_logs)


def test_create_test_prompt_handles_service_error(client: TestClient, monkeypatch):
    prompt_payload = _create_prompt(client)
    prompt_version_id = prompt_payload["current_version"]["id"]

    def raise_error(*_, **__):
        raise TestRunExecutionError("执行失败", status_code=422)

    monkeypatch.setattr("app.core.task_queue.execute_test_run", raise_error)

    response = client.post(
        "/api/v1/test_prompt/",
        json={
            "prompt_version_id": prompt_version_id,
            "model_name": "gpt-error",
            "temperature": 0.1,
            "top_p": 0.9,
            "repetitions": 1,
        },
    )
    assert response.status_code == 201

    assert task_queue.wait_for_idle(timeout=2.0)

    detail_resp = client.get(f"/api/v1/test_prompt/{response.json()['id']}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["status"] == "failed"
    assert detail["failure_reason"] == "执行失败"
    assert detail["schema"].get("last_error") == "执行失败"


def test_retry_failed_test_prompt(client: TestClient, monkeypatch):
    prompt_payload = _create_prompt(client)
    prompt_version_id = prompt_payload["current_version"]["id"]

    call_count = {"value": 0}

    def execute_with_retry(db, test_run):
        call_count["value"] += 1
        if call_count["value"] == 1:
            raise TestRunExecutionError("首次执行失败", status_code=500)
        test_run.status = "completed"
        test_run.last_error = None
        return test_run

    monkeypatch.setattr("app.core.task_queue.execute_test_run", execute_with_retry)

    response = client.post(
        "/api/v1/test_prompt/",
        json={
            "prompt_version_id": prompt_version_id,
            "model_name": "gpt-error",
            "temperature": 0.1,
            "top_p": 0.9,
            "repetitions": 1,
        },
    )
    assert response.status_code == 201

    assert task_queue.wait_for_idle(timeout=2.0)

    test_run_id = response.json()["id"]

    failed_detail_resp = client.get(f"/api/v1/test_prompt/{test_run_id}")
    assert failed_detail_resp.status_code == 200
    failed_payload = failed_detail_resp.json()
    assert failed_payload["status"] == "failed"
    assert failed_payload["failure_reason"] == "首次执行失败"
    assert failed_payload["schema"].get("last_error") == "首次执行失败"

    retry_resp = client.post(f"/api/v1/test_prompt/{test_run_id}/retry")
    assert retry_resp.status_code == 200
    retry_payload = retry_resp.json()
    assert retry_payload["status"] == "pending"
    assert retry_payload["failure_reason"] is None

    assert task_queue.wait_for_idle(timeout=2.0)

    final_detail_resp = client.get(f"/api/v1/test_prompt/{test_run_id}")
    assert final_detail_resp.status_code == 200
    final_payload = final_detail_resp.json()
    assert final_payload["status"] == "completed"
    assert final_payload["failure_reason"] is None
    final_schema = final_payload.get("schema") or {}
    assert final_schema.get("last_error") is None


def test_partial_failure_keeps_results(client: TestClient, monkeypatch):
    provider, model = _create_provider_with_model(client)
    prompt_payload = _create_prompt(client)
    prompt_version_id = prompt_payload["current_version"]["id"]

    def fake_invoke(
        *,
        provider,
        model,
        base_url,
        headers,
        payload,
        context,
    ):
        messages = payload.get("messages")
        if isinstance(messages, list) and len(messages) > 1:
            content = str(messages[1].get("content", ""))
            if "第 1" in content or "第一轮" in content:
                result = Result(
                    output="第一轮成功",
                    parsed_output=None,
                    tokens_used=123,
                    latency_ms=111,
                )
                usage = LLMUsageLog(
                    provider_id=provider.id,
                    model_id=model.id if model else None,
                    model_name=model.name if model else payload.get("model"),
                    source="test_run",
                    prompt_id=context.prompt_id,
                    prompt_version_id=context.prompt_version_id,
                    messages=messages,
                    parameters={
                        key: value
                        for key, value in payload.items()
                        if key not in {"model", "messages"}
                    }
                    or None,
                    response_text="第一轮成功",
                    temperature=payload.get("temperature"),
                    latency_ms=111,
                    prompt_tokens=50,
                    completion_tokens=60,
                    total_tokens=110,
                )
                result.test_run_id = context.test_run_id
                result.run_index = 1
                return result, usage
        raise TestRunExecutionError("第二轮接口报错", status_code=502)

    monkeypatch.setattr("app.services.test_run._invoke_llm_once", fake_invoke)

    response = client.post(
        "/api/v1/test_prompt/",
        json={
            "prompt_version_id": prompt_version_id,
            "model_name": model["name"],
            "temperature": 0.2,
            "top_p": 0.95,
            "repetitions": 2,
            "schema": {
                "llm_provider_id": provider["id"],
                "llm_model_id": model["id"],
                "conversation": [
                    {"role": "system", "content": "请保持专业"},
                    {"role": "user", "content": "第 {{run_index}} 次提问"},
                ],
            },
        },
    )
    assert response.status_code == 201
    test_run_id = response.json()["id"]

    assert task_queue.wait_for_idle(timeout=2.0)

    detail_resp = client.get(f"/api/v1/test_prompt/{test_run_id}")
    assert detail_resp.status_code == 200
    payload = detail_resp.json()
    assert payload["status"] == "failed"
    assert payload["failure_reason"] == "第二轮接口报错"
    assert len(payload["results"]) == 1
    assert payload["results"][0]["output"] == "第一轮成功"

    schema = payload["schema"]
    assert schema.get("last_error") == "第二轮接口报错"
    assert schema.get("last_error_status") == 502

    results_resp = client.get(f"/api/v1/test_prompt/{test_run_id}/results")
    assert results_resp.status_code == 200
    assert len(results_resp.json()) == 1


def test_update_test_prompt_allows_partial_fields(client: TestClient, monkeypatch):
    prompt_payload = _create_prompt(client)
    prompt_version_id = prompt_payload["current_version"]["id"]

    def fake_execute(db, test_run):
        test_run.status = "completed"
        return test_run

    monkeypatch.setattr("app.core.task_queue.execute_test_run", fake_execute)

    create_resp = client.post(
        "/api/v1/test_prompt/",
        json={
            "prompt_version_id": prompt_version_id,
            "model_name": "gpt-4o",
            "temperature": 0.2,
            "top_p": 0.9,
            "repetitions": 1,
        },
    )
    test_run = create_resp.json()

    assert task_queue.wait_for_idle(timeout=2.0)

    patch_resp = client.patch(
        f"/api/v1/test_prompt/{test_run['id']}",
        json={"notes": "更新说明", "status": "failed"},
    )
    assert patch_resp.status_code == 200
    payload = patch_resp.json()
    assert payload["notes"] == "更新说明"
    assert payload["status"] == "failed"


def test_get_test_prompt_not_found(client: TestClient):
    resp = client.get("/api/v1/test_prompt/9999")
    assert resp.status_code == 404
