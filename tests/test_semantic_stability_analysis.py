from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from app.schemas.analysis_module import AnalysisContext


def test_semantic_consistency_diversity_module_is_registered(client):
    response = client.get("/api/v1/analysis/modules")
    assert response.status_code == 200

    assert "semantic_consistency_diversity" in {
        item["module_id"] for item in response.json()
    }


def test_semantic_consistency_diversity_requires_embedding_model_configuration():
    from app.services.analysis_modules.semantic_stability import (
        execute_semantic_consistency_diversity_analysis,
    )

    data_frame = pd.DataFrame(
        [
            {
                "task_id": 1,
                "unit_id": 10,
                "unit_name": "单元A",
                "variable_case_hash": "hash-a",
                "variables": {"topic": "天气"},
                "output_text": "今天天气晴朗",
                "semantic_objective": "consistency",
                "run_index": 1,
            }
        ]
    )

    with pytest.raises(Exception, match="embedding"):
        execute_semantic_consistency_diversity_analysis(
            data_frame,
            {
                "embedding_provider_id": None,
                "embedding_model_id": None,
            },
            AnalysisContext(task_id="1"),
        )


def test_semantic_consistency_diversity_separates_variable_cases():
    from app.services.analysis_modules.semantic_stability import (
        execute_semantic_consistency_diversity_analysis,
    )

    data_frame = pd.DataFrame(
        [
            {
                "task_id": 1,
                "unit_id": 10,
                "unit_name": "单元A",
                "variable_case_hash": "hash-a",
                "variables": {"topic": "天气"},
                "output_text": "今天天气晴朗",
                "semantic_objective": "consistency",
                "run_index": 1,
            },
            {
                "task_id": 1,
                "unit_id": 10,
                "unit_name": "单元A",
                "variable_case_hash": "hash-b",
                "variables": {"topic": "美食"},
                "output_text": "今天推荐午餐",
                "semantic_objective": "consistency",
                "run_index": 1,
            },
        ]
    )

    class DummyEmbeddingClient:
        def __init__(self):
            self.calls: list[list[str]] = []

        def embed_texts(self, request):
            self.calls.append(list(request.texts))
            return SimpleNamespace(
                provider_id=request.provider_id,
                model_id=request.model_id,
                model_name="mock",
                embeddings=[[1.0, 0.0] for _ in request.texts],
            )

    result = execute_semantic_consistency_diversity_analysis(
        data_frame,
        {
            "embedding_provider_id": 7,
            "embedding_model_id": 8,
            "embedding_client": DummyEmbeddingClient(),
        },
        AnalysisContext(task_id="1"),
    )

    assert len(result.data_frame) == 2
    assert set(result.data_frame["variable_case_hash"]) == {"hash-a", "hash-b"}


def test_semantic_consistency_diversity_interprets_same_similarity_by_objective():
    from app.services.analysis_modules.semantic_stability import (
        execute_semantic_consistency_diversity_analysis,
    )

    base_rows = [
        {
            "task_id": 1,
            "unit_id": 10,
            "unit_name": "单元A",
            "variable_case_hash": "hash-a",
            "variables": {"topic": "天气"},
            "output_text": "今天天气晴朗",
            "run_index": 1,
        },
        {
            "task_id": 1,
            "unit_id": 10,
            "unit_name": "单元A",
            "variable_case_hash": "hash-a",
            "variables": {"topic": "天气"},
            "output_text": "杭州今天阳光很好",
            "run_index": 2,
        },
    ]

    class SameEmbeddingClient:
        def embed_texts(self, request):
            return SimpleNamespace(
                provider_id=request.provider_id,
                model_id=request.model_id,
                model_name="mock",
                embeddings=[[1.0, 0.0] for _ in request.texts],
            )

    def run_with_objective(objective: str):
        data_frame = pd.DataFrame(
            [dict(row, semantic_objective=objective) for row in base_rows]
        )
        return execute_semantic_consistency_diversity_analysis(
            data_frame,
            {
                "embedding_provider_id": 7,
                "embedding_model_id": 8,
                "embedding_client": SameEmbeddingClient(),
            },
            AnalysisContext(task_id="1"),
        )

    consistency = run_with_objective("consistency")
    diversity = run_with_objective("diversity")

    assert consistency.data_frame.loc[0, "interpretation_level"] == "ok"
    assert "稳定" in consistency.data_frame.loc[0, "interpretation"]
    assert diversity.data_frame.loc[0, "interpretation_level"] == "warning"
    assert "过度收敛" in diversity.data_frame.loc[0, "interpretation"]


def test_semantic_consistency_diversity_passes_max_samples_per_group_to_metrics():
    from app.services.analysis_modules.semantic_stability import (
        execute_semantic_consistency_diversity_analysis,
    )

    rows = [
        {
            "task_id": 1,
            "unit_id": 10,
            "unit_name": "单元A",
            "variable_case_hash": "hash-a",
            "variables": {"topic": "天气"},
            "output_text": f"回答 {index}",
            "semantic_objective": "consistency",
            "run_index": index,
        }
        for index in range(8)
    ]

    class ManyEmbeddingClient:
        def embed_texts(self, request):
            return SimpleNamespace(
                provider_id=request.provider_id,
                model_id=request.model_id,
                model_name="mock",
                embeddings=[
                    [1.0, float(index % 2)] for index, _ in enumerate(request.texts)
                ],
            )

    result = execute_semantic_consistency_diversity_analysis(
        pd.DataFrame(rows),
        {
            "embedding_provider_id": 7,
            "embedding_model_id": 8,
            "embedding_client": ManyEmbeddingClient(),
            "max_samples_per_group": 3,
        },
        AnalysisContext(task_id="1"),
    )

    first_row = result.data_frame.loc[0]
    assert first_row["sample_count"] == 8
    assert first_row["evaluated_sample_count"] == 3
    assert bool(first_row["is_sampled"]) is True
    assert first_row["pairwise_count"] == 3
    assert (
        result.extra["semantic_summary"]["group_summaries"][0]["evaluated_sample_count"]
        == 3
    )
