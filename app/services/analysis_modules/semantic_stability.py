from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping

import pandas as pd

from app.schemas.analysis_module import (
    AnalysisColumnMeta,
    AnalysisContext,
    AnalysisModuleDefinition,
    AnalysisParameterSpec,
    AnalysisParameterType,
    AnalysisResult,
)
from app.services.embedding_client import EmbeddingClient, EmbeddingRequest
from app.services.semantic_similarity import (
    SemanticOutput,
    build_variable_case_hash,
    calculate_group_metrics,
    interpret_metrics,
)

if TYPE_CHECKING:  # pragma: no cover - 仅用于类型提示
    from app.services.analysis_registry import AnalysisModuleRegistry

MODULE_ID = "semantic_consistency_diversity"
DEFAULT_MAX_SAMPLES_PER_GROUP = 100


def register_semantic_consistency_diversity_module(
    registry: "AnalysisModuleRegistry",
) -> None:
    """注册语义一致性与多样性分析模块。"""

    definition = AnalysisModuleDefinition(
        module_id=MODULE_ID,
        name="语义一致性与多样性",
        description="按测试单元与变量组合计算 embedding 语义相似度指标。",
        parameters=[
            AnalysisParameterSpec(
                key="embedding_provider_id",
                label="Embedding 提供方 ID",
                type=AnalysisParameterType.NUMBER,
                required=False,
                help_text="用于生成输出文本向量的提供方 ID。",
            ),
            AnalysisParameterSpec(
                key="embedding_model_id",
                label="Embedding 模型 ID",
                type=AnalysisParameterType.NUMBER,
                required=False,
                help_text="用于生成输出文本向量的模型 ID。",
            ),
            AnalysisParameterSpec(
                key="objective_override",
                label="语义目标覆盖",
                type=AnalysisParameterType.SELECT,
                required=False,
                options=["consistency", "diversity", "balanced"],
            ),
            AnalysisParameterSpec(
                key="max_samples_per_group",
                label="每组最大两两计算样本数",
                type=AnalysisParameterType.NUMBER,
                required=False,
                default=DEFAULT_MAX_SAMPLES_PER_GROUP,
                help_text="超过该数量时按组内样本均匀抽样计算两两相似度，避免大组计算量过高。",
            ),
        ],
        required_columns=[
            "task_id",
            "unit_id",
            "variable_case_hash",
            "output_text",
            "semantic_objective",
            "run_index",
        ],
        tags=["semantic", "embedding"],
        allow_llm=False,
    )
    registry.replace(definition, execute_semantic_consistency_diversity_analysis)


def execute_semantic_consistency_diversity_analysis(
    data_frame: pd.DataFrame,
    params: dict[str, Any],
    context: AnalysisContext,
) -> AnalysisResult:
    provider_id = _safe_int(params.get("embedding_provider_id"))
    model_id = _safe_int(params.get("embedding_model_id"))
    if provider_id is None or model_id is None:
        raise ValueError(
            "缺少 embedding 模型配置：请提供 embedding_provider_id 和 embedding_model_id。"
        )

    embedding_client = _resolve_embedding_client(params)
    working_df = _prepare_dataframe(data_frame)
    output_texts = working_df["output_text"].astype(str).tolist()
    embedding_result = embedding_client.embed_texts(
        EmbeddingRequest(
            provider_id=provider_id,
            model_id=model_id,
            texts=output_texts,
        )
    )

    if len(embedding_result.embeddings) != len(working_df):
        raise ValueError("embedding 返回数量与分析样本数量不一致。")

    working_df = working_df.assign(_embedding=embedding_result.embeddings)
    summary_df = _build_group_summary(working_df, params, context)
    return AnalysisResult(
        data_frame=summary_df,
        columns_meta=_build_columns_meta(),
        insights=_build_insights(summary_df),
        llm_usage=None,
        extra={
            "module_id": MODULE_ID,
            "charts": _build_chart_configs(summary_df),
            "semantic_summary": _build_semantic_summary(summary_df),
        },
    )


def _resolve_embedding_client(params: dict[str, Any]) -> Any:
    client = params.get("embedding_client")
    if client is not None:
        return client

    provider = params.get("embedding_provider")
    model = params.get("embedding_model")
    if provider is not None and model is not None:
        return EmbeddingClient(provider=provider, model=model)

    raise ValueError(
        "缺少 embedding client：请注入 embedding_client 或提供 embedding_provider/embedding_model。"
    )


def _prepare_dataframe(data_frame: pd.DataFrame) -> pd.DataFrame:
    working_df = data_frame.copy()
    if "variable_case_hash" not in working_df.columns:
        working_df["variable_case_hash"] = working_df["variables"].apply(
            lambda value: build_variable_case_hash(
                value if isinstance(value, Mapping) else None
            )
        )
    working_df = working_df.dropna(subset=["output_text"])
    working_df = working_df[working_df["output_text"].astype(str).str.strip() != ""]
    return working_df.reset_index(drop=True)


def _build_group_summary(
    working_df: pd.DataFrame,
    params: dict[str, Any],
    context: AnalysisContext,
) -> pd.DataFrame:
    objective_override = params.get("objective_override")
    max_samples_per_group = _resolve_max_samples_per_group(
        params.get("max_samples_per_group")
    )
    records: list[dict[str, Any]] = []
    grouped = working_df.groupby(
        ["task_id", "unit_id", "variable_case_hash"],
        dropna=False,
        sort=True,
    )
    for _, subset in grouped:
        outputs = [
            SemanticOutput(
                output_id=_output_id(row),
                text=str(row["output_text"]),
                embedding=row["_embedding"],
            )
            for _, row in subset.iterrows()
        ]
        metrics = calculate_group_metrics(
            outputs,
            max_pairwise_samples=max_samples_per_group,
        )
        objective = _resolve_objective(subset, objective_override)
        interpretation = interpret_metrics(metrics, objective)
        first_row = subset.iloc[0]
        records.append(
            {
                "task_id": first_row.get("task_id", context.task_id),
                "unit_id": first_row.get("unit_id"),
                "unit_name": first_row.get("unit_name"),
                "variable_case_hash": first_row.get("variable_case_hash"),
                "semantic_objective": objective,
                "sample_count": metrics.sample_count,
                "evaluated_sample_count": metrics.evaluated_sample_count,
                "is_sampled": metrics.is_sampled,
                "pairwise_count": metrics.pairwise_count,
                "status": metrics.status,
                "mean_pairwise_similarity": metrics.mean_pairwise_similarity,
                "min_pairwise_similarity": metrics.min_pairwise_similarity,
                "centroid_similarity_mean": metrics.centroid_similarity_mean,
                "semantic_dispersion": metrics.semantic_dispersion,
                "outlier_count": metrics.outlier_count,
                "outlier_output_ids": metrics.outlier_output_ids,
                "interpretation_level": interpretation.level,
                "interpretation": interpretation.summary,
            }
        )

    summary_df = pd.DataFrame(records)
    if not summary_df.empty:
        summary_df = summary_df.convert_dtypes()
    return summary_df


def _resolve_objective(subset: pd.DataFrame, override: Any) -> str:
    if isinstance(override, str) and override.strip():
        return override.strip()
    values = subset["semantic_objective"].dropna().astype(str).tolist()
    for value in values:
        if value.strip():
            return value.strip()
    return "consistency"


def _output_id(row: pd.Series) -> str:
    unit_id = row.get("unit_id")
    run_index = row.get("run_index")
    variable_hash = row.get("variable_case_hash")
    return f"{unit_id}:{variable_hash}:{run_index}"


def _build_columns_meta() -> list[AnalysisColumnMeta]:
    return [
        AnalysisColumnMeta(name="unit_name", label="测试单元"),
        AnalysisColumnMeta(name="variable_case_hash", label="变量组合"),
        AnalysisColumnMeta(name="semantic_objective", label="语义目标"),
        AnalysisColumnMeta(name="sample_count", label="样本数", visualizable=["bar"]),
        AnalysisColumnMeta(
            name="evaluated_sample_count",
            label="参与两两计算样本数",
            visualizable=["bar"],
        ),
        AnalysisColumnMeta(name="is_sampled", label="是否采样计算"),
        AnalysisColumnMeta(name="pairwise_count", label="两两比较次数"),
        AnalysisColumnMeta(
            name="mean_pairwise_similarity",
            label="平均语义相似度",
            visualizable=["bar"],
        ),
        AnalysisColumnMeta(
            name="semantic_dispersion",
            label="语义离散度",
            visualizable=["bar"],
        ),
        AnalysisColumnMeta(
            name="outlier_count", label="离群数量", visualizable=["bar"]
        ),
        AnalysisColumnMeta(name="interpretation", label="目标解释"),
    ]


def _build_insights(summary_df: pd.DataFrame) -> list[str]:
    if summary_df.empty:
        return ["暂无可分析的语义输出样本。"]
    warnings = summary_df[summary_df["interpretation_level"] == "warning"]
    if not warnings.empty:
        return warnings["interpretation"].dropna().astype(str).unique().tolist()
    return ["语义一致性与多样性分析已完成，未发现明显目标偏离。"]


def _build_chart_configs(summary_df: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {
            "id": "mean_pairwise_similarity",
            "type": "bar",
            "title": "平均语义相似度",
            "x": "variable_case_hash",
            "y": "mean_pairwise_similarity",
            "meta": {"row_count": int(len(summary_df))},
        },
        {
            "id": "semantic_dispersion",
            "type": "bar",
            "title": "语义离散度",
            "x": "variable_case_hash",
            "y": "semantic_dispersion",
            "meta": {"row_count": int(len(summary_df))},
        },
    ]


def _build_semantic_summary(summary_df: pd.DataFrame) -> dict[str, Any]:
    group_summaries = []
    for row in summary_df.to_dict(orient="records"):
        group_summaries.append(
            {
                "unit_id": row.get("unit_id"),
                "unit_name": row.get("unit_name"),
                "variable_case_hash": row.get("variable_case_hash"),
                "semantic_objective": row.get("semantic_objective"),
                "sample_count": row.get("sample_count"),
                "evaluated_sample_count": row.get("evaluated_sample_count"),
                "is_sampled": row.get("is_sampled"),
                "pairwise_count": row.get("pairwise_count"),
                "mean_pairwise_similarity": row.get("mean_pairwise_similarity"),
                "semantic_dispersion": row.get("semantic_dispersion"),
                "outlier_count": row.get("outlier_count"),
                "interpretation": row.get("interpretation"),
            }
        )
    return {
        "group_count": len(group_summaries),
        "group_summaries": group_summaries,
    }


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value == value else None
    if isinstance(value, str) and value.strip():
        try:
            return int(float(value))
        except ValueError:
            return None
    return None


def _resolve_max_samples_per_group(value: Any) -> int:
    parsed = _safe_int(value)
    if parsed is None or parsed < 2:
        return DEFAULT_MAX_SAMPLES_PER_GROUP
    return parsed


__all__ = [
    "DEFAULT_MAX_SAMPLES_PER_GROUP",
    "MODULE_ID",
    "execute_semantic_consistency_diversity_analysis",
    "register_semantic_consistency_diversity_module",
]
