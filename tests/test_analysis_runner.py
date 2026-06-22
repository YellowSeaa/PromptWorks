from __future__ import annotations

from app.models.prompt_test import (
    PromptTestExperiment,
    PromptTestExperimentStatus,
    PromptTestTask,
    PromptTestTaskStatus,
    PromptTestUnit,
)
from app.services.analysis_runner import _build_prompt_test_dataframe


def test_prompt_test_dataframe_includes_semantic_analysis_fields(db_session):
    task = PromptTestTask(
        name="语义分析任务",
        status=PromptTestTaskStatus.COMPLETED,
        config=None,
    )
    unit = PromptTestUnit(
        task=task,
        name="单元A",
        model_name="gpt-mini",
        llm_provider_id=None,
        temperature=0.2,
        top_p=0.9,
        rounds=2,
        variables={"topic": "天气", "cases": [{"city": "杭州"}]},
        extra={"semantic_objective": "diversity"},
    )
    experiment = PromptTestExperiment(
        unit=unit,
        sequence=1,
        status=PromptTestExperimentStatus.COMPLETED,
        outputs=[
            {
                "run_index": 1,
                "output_text": "今天天气晴朗",
                "variables": {"city": "杭州"},
            },
            {
                "run_index": 2,
                "output_text": "杭州今天阳光很好",
                "variables": {"city": "杭州"},
            },
        ],
    )

    db_session.add_all([task, unit, experiment])
    db_session.commit()

    dataframe = _build_prompt_test_dataframe(task)

    assert list(dataframe.columns) == [
        "task_id",
        "unit_id",
        "unit_name",
        "experiment_id",
        "run_index",
        "latency_ms",
        "tokens_used",
        "total_cost",
        "cost_currency",
        "temperature",
        "temperature_mode",
        "parameter_set",
        "output_text",
        "variables",
        "variable_case_hash",
        "semantic_objective",
    ]
    assert dataframe.loc[0, "output_text"] == "今天天气晴朗"
    assert dataframe.loc[0, "variables"] == {"city": "杭州"}
    assert dataframe.loc[0, "semantic_objective"] == "diversity"
    assert dataframe.loc[0, "unit_id"] == unit.id
    assert dataframe.loc[0, "unit_name"] == "单元A"
    assert dataframe.loc[0, "run_index"] == 1
    assert (
        dataframe.loc[1, "variable_case_hash"] == dataframe.loc[0, "variable_case_hash"]
    )


def test_prompt_test_dataframe_keeps_samples_even_when_variable_data_is_sparse(
    db_session,
):
    task = PromptTestTask(
        name="语义分析任务2",
        status=PromptTestTaskStatus.COMPLETED,
        config=None,
    )
    unit = PromptTestUnit(
        task=task,
        name="单元B",
        model_name="gpt-mini",
        llm_provider_id=None,
        temperature=0.2,
        top_p=0.9,
        rounds=1,
        variables=None,
        extra={},
    )
    experiment = PromptTestExperiment(
        unit=unit,
        sequence=1,
        status=PromptTestExperimentStatus.COMPLETED,
        outputs=[{"run_index": 1, "output_text": "仅一条输出", "variables": None}],
    )

    db_session.add_all([task, unit, experiment])
    db_session.commit()

    dataframe = _build_prompt_test_dataframe(task)

    assert len(dataframe) == 1
    assert dataframe.loc[0, "variables"] is None
    assert dataframe.loc[0, "semantic_objective"] == "consistency"
