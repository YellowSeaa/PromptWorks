from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import select

from app.models.llm_provider import LLMModel, LLMProvider
from app.models.prompt import Prompt, PromptClass, PromptVersion
from app.models.prompt_test import (
    PromptTestExperiment,
    PromptTestExperimentStatus,
    PromptTestOptimizationRecommendationStatus,
    PromptTestOutputScore,
    PromptTestOutputScoreStatus,
    PromptTestTask,
    PromptTestUnit,
)
from app.services import prompt_test_ai_scoring


class DummyResponse:
    """用于伪造 OpenAI 兼容接口响应。"""

    def __init__(self, payload: dict[str, Any], *, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.elapsed = timedelta(milliseconds=25)
        self.text = str(payload)

    def json(self) -> dict[str, Any]:
        return self._payload


def _create_prompt_version(db_session) -> PromptVersion:
    prompt_class = PromptClass(name="评分测试分类")
    prompt = Prompt(
        name="客服回复 Prompt",
        description="评估客服回复是否准确、友好且可执行。",
        prompt_class=prompt_class,
    )
    version = PromptVersion(
        prompt=prompt,
        version="v1",
        content="你是一名客服助手，请基于用户问题给出准确回复。",
    )
    prompt.current_version = version
    db_session.add_all([prompt_class, prompt, version])
    db_session.commit()
    return version


def _create_provider_and_model(
    db_session, *, name: str = "judge-pro", concurrency_limit: int = 4
) -> LLMModel:
    provider = LLMProvider(
        provider_name=f"Provider {name}",
        provider_key=None,
        api_key="fake-key",
        is_custom=True,
        base_url="https://llm.fake/api",
    )
    model = LLMModel(provider=provider, name=name, concurrency_limit=concurrency_limit)
    db_session.add_all([provider, model])
    db_session.commit()
    return model


def _create_completed_experiment(db_session, model: LLMModel) -> PromptTestExperiment:
    prompt_version = _create_prompt_version(db_session)
    task = PromptTestTask(
        name="评分任务",
        description="请用中文评估输出质量。",
        prompt_version_id=prompt_version.id,
        config={
            "ai_scoring": {
                "enabled": True,
                "evaluator_provider_id": model.provider_id,
                "evaluator_model_id": model.id,
                "evaluator_model_name": model.name,
                "language": "zh-CN",
            }
        },
    )
    unit = PromptTestUnit(
        task=task,
        prompt_version_id=prompt_version.id,
        name="客服单元",
        model_name="tested-model",
        llm_provider_id=model.provider_id,
        rounds=1,
        prompt_template="用户问题：{question}",
        variables={"cases": [{"question": "如何退款？"}]},
        temperature=0.7,
    )
    experiment = PromptTestExperiment(
        unit=unit,
        sequence=1,
        status=PromptTestExperimentStatus.COMPLETED,
        outputs=[
            {
                "run_index": 1,
                "messages": [{"role": "user", "content": "用户问题：如何退款？"}],
                "variables": {"question": "如何退款？"},
                "output_text": "您可以在订单详情页申请退款。",
                "latency_ms": 10,
                "total_tokens": 20,
            }
        ],
        metrics={"rounds": 1},
        finished_at=datetime.now(UTC),
    )
    db_session.add_all([task, unit, experiment])
    db_session.commit()
    return experiment


def test_score_output_retries_twice_then_persists_success(db_session, monkeypatch):
    model = _create_provider_and_model(db_session)
    experiment = _create_completed_experiment(db_session, model)
    calls = 0

    def fake_post(*_, **__):
        nonlocal calls
        calls += 1
        if calls < 3:
            return DummyResponse({"error": {"message": "temporary"}}, status_code=503)
        return DummyResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"overall_score": 88, "dimension_scores": {"准确性": 90, "完整性": 86}, "reason": "回复准确且清晰。"}'
                        }
                    }
                ],
                "usage": {"total_tokens": 42},
            }
        )

    monkeypatch.setattr("app.services.prompt_test_ai_scoring.httpx.post", fake_post)

    score = prompt_test_ai_scoring.score_experiment_output(
        db_session,
        experiment=experiment,
        output=experiment.outputs[0],
        scoring_config=prompt_test_ai_scoring.AIScoringConfig(
            enabled=True,
            evaluator_provider_id=model.provider_id,
            evaluator_model_id=model.id,
            evaluator_model_name=model.name,
            language="zh-CN",
        ),
    )
    db_session.commit()

    assert calls == 3
    assert score.status == PromptTestOutputScoreStatus.COMPLETED
    assert score.retry_count == 2
    assert score.overall_score == 88
    assert score.dimension_scores == {"准确性": 90.0, "完整性": 86.0}
    assert score.reason == "回复准确且清晰。"
    assert score.language == "zh-CN"


def test_score_output_records_failure_after_retries(db_session, monkeypatch):
    model = _create_provider_and_model(db_session)
    experiment = _create_completed_experiment(db_session, model)

    def fake_post(*_, **__):
        return DummyResponse({"error": {"message": "unavailable"}}, status_code=502)

    monkeypatch.setattr("app.services.prompt_test_ai_scoring.httpx.post", fake_post)

    score = prompt_test_ai_scoring.score_experiment_output(
        db_session,
        experiment=experiment,
        output=experiment.outputs[0],
        scoring_config=prompt_test_ai_scoring.AIScoringConfig(
            enabled=True,
            evaluator_provider_id=model.provider_id,
            evaluator_model_id=model.id,
            evaluator_model_name=model.name,
            language="en-US",
        ),
    )
    db_session.commit()

    assert score.status == PromptTestOutputScoreStatus.FAILED
    assert score.retry_count == 2
    assert "HTTP 502" in (score.error or "")
    assert score.language == "en-US"


def test_build_task_score_summary_uses_successful_scores_only(db_session):
    model = _create_provider_and_model(db_session)
    experiment = _create_completed_experiment(db_session, model)
    failed = PromptTestOutputScore(
        task_id=experiment.unit.task_id,
        unit_id=experiment.unit_id,
        experiment_id=experiment.id,
        run_index=1,
        status=PromptTestOutputScoreStatus.FAILED,
        evaluator_provider_id=model.provider_id,
        evaluator_model_id=model.id,
        evaluator_model_name=model.name,
        language="zh-CN",
        retry_count=2,
        error="评分失败",
    )
    success_a = PromptTestOutputScore(
        task_id=experiment.unit.task_id,
        unit_id=experiment.unit_id,
        experiment_id=experiment.id,
        run_index=2,
        status=PromptTestOutputScoreStatus.COMPLETED,
        evaluator_provider_id=model.provider_id,
        evaluator_model_id=model.id,
        evaluator_model_name=model.name,
        language="zh-CN",
        overall_score=80,
        dimension_scores={"准确性": 90, "完整性": 70},
        reason="可用。",
    )
    success_b = PromptTestOutputScore(
        task_id=experiment.unit.task_id,
        unit_id=experiment.unit_id,
        experiment_id=experiment.id,
        run_index=3,
        status=PromptTestOutputScoreStatus.COMPLETED,
        evaluator_provider_id=model.provider_id,
        evaluator_model_id=model.id,
        evaluator_model_name=model.name,
        language="zh-CN",
        overall_score=90,
        dimension_scores={"准确性": 100, "完整性": 80},
        reason="更稳定。",
    )
    db_session.add_all([failed, success_a, success_b])
    db_session.commit()

    summary = prompt_test_ai_scoring.build_task_score_summary(
        db_session, experiment.unit.task_id
    )

    unit_summary = summary["unit_summaries"][str(experiment.unit_id)]
    assert unit_summary["count"] == 2
    assert unit_summary["avg_score"] == 85
    assert unit_summary["variance"] == 25
    assert unit_summary["stddev"] == 5
    assert unit_summary["dimension_stats"]["准确性"]["avg"] == 95
    assert unit_summary["dimension_stats"]["准确性"]["variance"] == 25


def test_parse_ai_scoring_config_and_update_task_status(db_session):
    model = _create_provider_and_model(db_session)
    task = PromptTestTask(name="配置任务", config={})
    db_session.add(task)
    db_session.commit()

    scoring_config = prompt_test_ai_scoring.AIScoringConfig(
        enabled=True,
        evaluator_provider_id=model.provider_id,
        evaluator_model_id=model.id,
        evaluator_model_name=model.name,
        language="en-US",
    )
    prompt_test_ai_scoring.update_task_ai_scoring_status(
        task,
        scoring_config=scoring_config,
        status="running",
        progress={"current": 1, "total": 2, "percentage": 50},
    )
    parsed = prompt_test_ai_scoring.parse_ai_scoring_config(task.config)

    assert parsed == scoring_config
    assert task.config["ai_scoring"]["status"] == "running"
    assert task.config["ai_scoring"]["progress"]["percentage"] == 50
    assert prompt_test_ai_scoring.parse_ai_scoring_config({"ai_scoring": {}}) is None


def test_score_task_outputs_scores_existing_latest_outputs(db_session, monkeypatch):
    model = _create_provider_and_model(db_session)
    experiment = _create_completed_experiment(db_session, model)

    def fake_post(*_, **__):
        return DummyResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"overall_score": 76, "dimension_scores": {"准确性": 78}, "reason": "可以继续优化。"}'
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr("app.services.prompt_test_ai_scoring.httpx.post", fake_post)

    summary = prompt_test_ai_scoring.score_task_outputs(
        db_session, experiment.unit.task_id
    )
    db_session.commit()

    assert summary["status"]["completed"] == 1
    assert summary["unit_summaries"][str(experiment.unit_id)]["avg_score"] == 76
    refreshed_task = db_session.get(PromptTestTask, experiment.unit.task_id)
    assert refreshed_task.config["ai_scoring"]["status"] == "completed"
    assert refreshed_task.config["ai_scoring"]["progress"]["percentage"] == 100


def test_create_optimization_recommendation_success(db_session, monkeypatch):
    model = _create_provider_and_model(db_session)
    experiment = _create_completed_experiment(db_session, model)
    db_session.add(
        PromptTestOutputScore(
            task_id=experiment.unit.task_id,
            unit_id=experiment.unit_id,
            experiment_id=experiment.id,
            run_index=1,
            status=PromptTestOutputScoreStatus.COMPLETED,
            evaluator_provider_id=model.provider_id,
            evaluator_model_id=model.id,
            evaluator_model_name=model.name,
            language="zh-CN",
            overall_score=72,
            dimension_scores={"准确性": 72},
            reason="回答略简略。",
        )
    )
    db_session.commit()

    def fake_post(*_, **__):
        return DummyResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"overall_advice": "补充步骤说明。", "temperature_advice": "保持 0.7。", "model_advice": "当前模型可继续使用。", "prompt_revision": "请分步骤回答。", "validation_plan": "用退款问题重测。"}'
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr("app.services.prompt_test_ai_scoring.httpx.post", fake_post)

    recommendation = prompt_test_ai_scoring.create_optimization_recommendation(
        db_session,
        task_id=experiment.unit.task_id,
        evaluator_provider_id=model.provider_id,
        evaluator_model_id=model.id,
        evaluator_model_name=model.name,
        language="zh-CN",
    )
    latest = prompt_test_ai_scoring.get_latest_recommendation(
        db_session, experiment.unit.task_id
    )

    assert recommendation.status == PromptTestOptimizationRecommendationStatus.COMPLETED
    assert recommendation.content["prompt_revision"] == "请分步骤回答。"
    assert latest is recommendation


def test_prompt_test_ai_scoring_api_triggers_and_retries_score(
    client, db_session, monkeypatch
):
    model = _create_provider_and_model(db_session)
    experiment = _create_completed_experiment(db_session, model)

    def fake_score_task(session, task_id, *, force=False):
        score = PromptTestOutputScore(
            task_id=task_id,
            unit_id=experiment.unit_id,
            experiment_id=experiment.id,
            run_index=1,
            status=PromptTestOutputScoreStatus.FAILED,
            evaluator_provider_id=model.provider_id,
            evaluator_model_id=model.id,
            evaluator_model_name=model.name,
            language="zh-CN",
            retry_count=2,
            error="评分失败",
        )
        session.add(score)
        session.flush()
        return prompt_test_ai_scoring.build_task_score_summary(session, task_id)

    def fake_retry_score(session, score):
        score.status = PromptTestOutputScoreStatus.COMPLETED
        score.overall_score = 91
        score.dimension_scores = {"准确性": 91}
        score.reason = "重试成功。"
        score.error = None
        session.flush()
        return score

    monkeypatch.setattr(
        "app.api.v1.endpoints.prompt_test_tasks.score_task_outputs", fake_score_task
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.prompt_test_tasks.retry_output_score", fake_retry_score
    )

    trigger_resp = client.post(
        f"/api/v1/prompt-test/tasks/{experiment.unit.task_id}/ai-scoring",
        json={
            "enabled": True,
            "evaluator_provider_id": model.provider_id,
            "evaluator_model_id": model.id,
            "evaluator_model_name": model.name,
            "language": "zh-CN",
        },
    )
    assert trigger_resp.status_code == 200
    assert trigger_resp.json()["status"]["language"] == "zh-CN"

    list_resp = client.get(
        f"/api/v1/prompt-test/tasks/{experiment.unit.task_id}/ai-scores"
    )
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert body["scores"][0]["status"] == PromptTestOutputScoreStatus.FAILED.value

    score_id = body["scores"][0]["id"]
    retry_resp = client.post(f"/api/v1/prompt-test/output-scores/{score_id}/retry")
    assert retry_resp.status_code == 200
    assert retry_resp.json()["status"] == PromptTestOutputScoreStatus.COMPLETED.value
    assert retry_resp.json()["overall_score"] == 91


def test_optimization_recommendation_requires_valid_scores(client, db_session):
    model = _create_provider_and_model(db_session)
    experiment = _create_completed_experiment(db_session, model)

    response = client.post(
        f"/api/v1/prompt-test/tasks/{experiment.unit.task_id}/optimization-recommendations",
        json={
            "evaluator_provider_id": model.provider_id,
            "evaluator_model_id": model.id,
            "evaluator_model_name": model.name,
            "language": "zh-CN",
        },
    )

    assert response.status_code == 422
    assert "有效评分" in response.json()["detail"]


def test_parallel_limit_splits_shared_model_concurrency():
    different = prompt_test_ai_scoring.resolve_parallel_limits(
        test_model_id=1,
        evaluator_model_id=2,
        test_concurrency_limit=6,
        evaluator_concurrency_limit=4,
    )
    assert different.test_limit == 6
    assert different.scoring_limit == 4

    shared = prompt_test_ai_scoring.resolve_parallel_limits(
        test_model_id=1,
        evaluator_model_id=1,
        test_concurrency_limit=5,
        evaluator_concurrency_limit=5,
    )
    assert shared.test_limit == 2
    assert shared.scoring_limit == 3

    single = prompt_test_ai_scoring.resolve_parallel_limits(
        test_model_id=1,
        evaluator_model_id=1,
        test_concurrency_limit=1,
        evaluator_concurrency_limit=1,
    )
    assert single.test_limit == 1
    assert single.scoring_limit == 1
    assert single.shared_single_lane is True
