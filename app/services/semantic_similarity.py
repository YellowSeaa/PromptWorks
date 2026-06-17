from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any, Mapping, Sequence


INSUFFICIENT_SAMPLES = "insufficient_samples"
OK = "ok"


@dataclass(frozen=True, slots=True)
class SemanticOutput:
    output_id: str
    text: str
    embedding: Sequence[float]


@dataclass(frozen=True, slots=True)
class SemanticGroupMetrics:
    sample_count: int
    status: str
    mean_pairwise_similarity: float | None = None
    min_pairwise_similarity: float | None = None
    centroid_similarity_mean: float | None = None
    semantic_dispersion: float | None = None
    outlier_count: int = 0
    outlier_output_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SemanticInterpretation:
    level: str
    summary: str


def build_variable_case_hash(variables: Mapping[str, Any] | None) -> str:
    canonical = _canonicalize_value(variables or {})
    payload = json.dumps(
        canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_comparable_group(
    task_id: str | int,
    unit_id: str | int,
    variables: Mapping[str, Any] | None,
) -> str:
    variable_case_hash = build_variable_case_hash(variables)
    return f"{task_id}:{unit_id}:{variable_case_hash}"


def normalize_vector(vector: Sequence[float]) -> list[float]:
    values = [float(value) for value in vector]
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        return [0.0 for _ in values]
    return [value / norm for value in values]


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError("向量维度不一致，无法计算余弦相似度。")
    normalized_a = normalize_vector(a)
    normalized_b = normalize_vector(b)
    return sum(
        left * right for left, right in zip(normalized_a, normalized_b, strict=True)
    )


def calculate_group_metrics(outputs: list[SemanticOutput]) -> SemanticGroupMetrics:
    sample_count = len(outputs)
    if sample_count < 2:
        return SemanticGroupMetrics(
            sample_count=sample_count,
            status=INSUFFICIENT_SAMPLES,
        )

    _ensure_same_dimensions(outputs)
    normalized_embeddings = [normalize_vector(output.embedding) for output in outputs]
    pairwise_similarities = [
        cosine_similarity(left, right)
        for left, right in combinations(normalized_embeddings, 2)
    ]
    centroid = _build_centroid(normalized_embeddings)
    centroid_similarities = [
        cosine_similarity(embedding, centroid) for embedding in normalized_embeddings
    ]
    centroid_similarity_mean = _mean(centroid_similarities)
    outlier_output_ids = _detect_outlier_ids(outputs, centroid_similarities)

    return SemanticGroupMetrics(
        sample_count=sample_count,
        status=OK,
        mean_pairwise_similarity=_mean(pairwise_similarities),
        min_pairwise_similarity=min(pairwise_similarities),
        centroid_similarity_mean=centroid_similarity_mean,
        semantic_dispersion=1 - centroid_similarity_mean,
        outlier_count=len(outlier_output_ids),
        outlier_output_ids=outlier_output_ids,
    )


def interpret_metrics(
    metrics: SemanticGroupMetrics, objective: str
) -> SemanticInterpretation:
    if metrics.status == INSUFFICIENT_SAMPLES:
        return SemanticInterpretation(
            level="info",
            summary="样本数不足，暂无法判断语义稳定性。",
        )

    similarity = metrics.mean_pairwise_similarity
    if similarity is None:
        return SemanticInterpretation(level="info", summary="缺少可解释的相似度指标。")

    normalized_objective = objective.strip().lower()
    if normalized_objective == "consistency":
        if similarity < 0.8:
            return SemanticInterpretation(
                level="warning",
                summary="一致性目标下出现低相似度结果，存在语义漂移风险。",
            )
        return SemanticInterpretation(level="ok", summary="语义一致性表现稳定。")

    if normalized_objective == "diversity":
        if similarity > 0.85:
            return SemanticInterpretation(
                level="warning",
                summary="多样性目标下相似度偏高，存在过度收敛风险。",
            )
        return SemanticInterpretation(level="ok", summary="语义多样性处于可接受范围。")

    if normalized_objective == "balanced":
        if similarity > 0.85:
            return SemanticInterpretation(
                level="warning",
                summary="平衡目标下相似度偏高，存在过度收敛风险。",
            )
        if similarity < 0.55:
            return SemanticInterpretation(
                level="warning",
                summary="平衡目标下相似度偏低，存在语义漂移风险。",
            )
        return SemanticInterpretation(level="ok", summary="语义相似度处于平衡区间。")

    return SemanticInterpretation(
        level="info", summary="未识别的语义目标，仅返回中性指标。"
    )


def _canonicalize_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize_value(value[key])
            for key in sorted(value.keys(), key=str)
        }
    if isinstance(value, list):
        return [_canonicalize_value(item) for item in value]
    if isinstance(value, tuple):
        return {
            "__type__": "tuple",
            "items": [_canonicalize_value(item) for item in value],
        }
    if isinstance(value, (str, int, float, bool)) or value is None:
        return {
            "__type__": type(value).__name__,
            "value": value,
        }
    return {
        "__type__": type(value).__name__,
        "value": repr(value),
    }


def _ensure_same_dimensions(outputs: list[SemanticOutput]) -> None:
    dimensions = {len(output.embedding) for output in outputs}
    if len(dimensions) != 1:
        raise ValueError("同一语义分组内的 embedding 向量维度必须一致。")


def _build_centroid(normalized_embeddings: list[list[float]]) -> list[float]:
    dimensions = len(normalized_embeddings[0])
    return [
        _mean([embedding[index] for embedding in normalized_embeddings])
        for index in range(dimensions)
    ]


def _detect_outlier_ids(
    outputs: list[SemanticOutput],
    centroid_similarities: list[float],
) -> list[str]:
    if len(centroid_similarities) < 3:
        return []
    mean_similarity = _mean(centroid_similarities)
    variance = _mean(
        [(similarity - mean_similarity) ** 2 for similarity in centroid_similarities]
    )
    threshold = min(0.65, mean_similarity - math.sqrt(variance))
    return [
        output.output_id
        for output, similarity in zip(outputs, centroid_similarities, strict=True)
        if similarity < threshold
    ]


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)
