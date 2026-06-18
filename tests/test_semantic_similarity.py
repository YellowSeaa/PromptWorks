import math

import pytest

from app.services.semantic_similarity import (
    SemanticOutput,
    build_comparable_group,
    build_variable_case_hash,
    calculate_group_metrics,
    cosine_similarity,
    interpret_metrics,
    normalize_vector,
)


def test_variable_case_hash_ignores_key_order() -> None:
    first = build_variable_case_hash({"city": "杭州", "days": 3})
    second = build_variable_case_hash({"days": 3, "city": "杭州"})

    assert first == second


def test_variable_case_hash_preserves_value_type() -> None:
    number_hash = build_variable_case_hash({"count": 1})
    string_hash = build_variable_case_hash({"count": "1"})

    assert number_hash != string_hash


def test_variable_case_hash_returns_stable_value_for_empty_variables() -> None:
    assert build_variable_case_hash(None) == build_variable_case_hash({})
    assert build_variable_case_hash({}) == build_variable_case_hash({})


def test_comparable_group_combines_task_unit_and_variable_case_hash() -> None:
    first = build_comparable_group("task-1", "unit-1", {"topic": "A"})
    second = build_comparable_group("task-1", "unit-1", {"topic": "B"})
    same_as_first = build_comparable_group("task-1", "unit-1", {"topic": "A"})

    assert first == same_as_first
    assert first != second
    assert first.startswith("task-1:unit-1:")


def test_cosine_similarity_for_identical_and_orthogonal_vectors() -> None:
    assert cosine_similarity([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)


def test_normalize_vector_returns_unit_vector() -> None:
    normalized = normalize_vector([3, 4])

    assert normalized == pytest.approx([0.6, 0.8])
    assert math.sqrt(sum(value * value for value in normalized)) == pytest.approx(1.0)


def test_calculate_group_metrics_returns_insufficient_samples_for_single_output() -> (
    None
):
    metrics = calculate_group_metrics(
        [
            SemanticOutput(
                output_id="out-1",
                text="回答一",
                embedding=[1, 0],
            )
        ]
    )

    assert metrics.status == "insufficient_samples"
    assert metrics.sample_count == 1
    assert metrics.mean_pairwise_similarity is None
    assert metrics.min_pairwise_similarity is None
    assert metrics.outlier_count == 0


def test_calculate_group_metrics_identifies_outlier_output() -> None:
    metrics = calculate_group_metrics(
        [
            SemanticOutput(output_id="out-1", text="相似回答一", embedding=[1, 0]),
            SemanticOutput(
                output_id="out-2", text="相似回答二", embedding=[0.98, 0.02]
            ),
            SemanticOutput(output_id="out-3", text="偏离回答", embedding=[0, 1]),
        ]
    )

    assert metrics.status == "ok"
    assert metrics.sample_count == 3
    assert metrics.mean_pairwise_similarity == pytest.approx(0.34, abs=0.02)
    assert metrics.min_pairwise_similarity == pytest.approx(0.0, abs=0.02)
    assert metrics.centroid_similarity_mean == pytest.approx(0.75, abs=0.03)
    assert metrics.semantic_dispersion == pytest.approx(0.25, abs=0.03)
    assert metrics.outlier_count == 1
    assert metrics.outlier_output_ids == ["out-3"]


def test_calculate_group_metrics_samples_large_groups_for_pairwise_work() -> None:
    outputs = [
        SemanticOutput(
            output_id=f"out-{index}",
            text=f"回答{index}",
            embedding=[1.0, float(index % 3)],
        )
        for index in range(10)
    ]

    metrics = calculate_group_metrics(outputs, max_pairwise_samples=4)

    assert metrics.status == "ok"
    assert metrics.sample_count == 10
    assert metrics.evaluated_sample_count == 4
    assert metrics.is_sampled is True
    assert metrics.pairwise_count == 6
    assert metrics.mean_pairwise_similarity is not None
    assert metrics.centroid_similarity_mean is not None


def test_interpret_metrics_flags_consistency_drift() -> None:
    metrics = calculate_group_metrics(
        [
            SemanticOutput(output_id="out-1", text="回答一", embedding=[1, 0]),
            SemanticOutput(output_id="out-2", text="回答二", embedding=[0, 1]),
        ]
    )

    interpretation = interpret_metrics(metrics, "consistency")

    assert interpretation.level == "warning"
    assert "语义漂移" in interpretation.summary


def test_interpret_metrics_flags_diversity_convergence() -> None:
    metrics = calculate_group_metrics(
        [
            SemanticOutput(output_id="out-1", text="回答一", embedding=[1, 0]),
            SemanticOutput(output_id="out-2", text="回答二", embedding=[1, 0]),
        ]
    )

    interpretation = interpret_metrics(metrics, "diversity")

    assert interpretation.level == "warning"
    assert "过度收敛" in interpretation.summary


@pytest.mark.parametrize(
    ("vectors", "expected_text"),
    [
        (([1, 0], [1, 0]), "过度收敛"),
        (([1, 0], [0, 1]), "语义漂移"),
    ],
)
def test_interpret_metrics_flags_balanced_range_issues(
    vectors: tuple[list[int], list[int]], expected_text: str
) -> None:
    metrics = calculate_group_metrics(
        [
            SemanticOutput(output_id="out-1", text="回答一", embedding=vectors[0]),
            SemanticOutput(output_id="out-2", text="回答二", embedding=vectors[1]),
        ]
    )

    interpretation = interpret_metrics(metrics, "balanced")

    assert interpretation.level == "warning"
    assert expected_text in interpretation.summary
