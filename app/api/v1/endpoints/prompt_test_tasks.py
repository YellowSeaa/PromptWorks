from __future__ import annotations

from datetime import UTC, datetime
from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.prompt_test_task_queue import enqueue_prompt_test_task
from app.db.session import get_db
from app.models.prompt import PromptVersion
from app.models.prompt_test import (
    PromptTestExperiment,
    PromptTestExperimentStatus,
    PromptTestOptimizationRecommendation,
    PromptTestOutputScore,
    PromptTestTask,
    PromptTestTaskStatus,
    PromptTestUnit,
)
from app.schemas.prompt_test import (
    PromptTestExperimentCreate,
    PromptTestExperimentRead,
    PromptTestAIScoreSummaryRead,
    PromptTestAIScoringRequest,
    PromptTestOptimizationRecommendationRead,
    PromptTestOptimizationRecommendationRequest,
    PromptTestOutputScoreRead,
    PromptTestTaskCreate,
    PromptTestTaskRead,
    PromptTestTaskUpdate,
    PromptTestUnitCreate,
    PromptTestUnitRead,
    PromptTestUnitUpdate,
)
from app.services.prompt_test_engine import (
    PromptTestExecutionError,
    execute_prompt_test_experiment,
)
from app.services.prompt_test_ai_scoring import (
    AIScoringConfig,
    PromptTestAIScoringError,
    build_task_score_summary,
    create_optimization_recommendation,
    get_latest_recommendation,
    list_recommendations,
    retry_output_score,
    score_task_outputs,
    update_task_ai_scoring_status,
)

router = APIRouter(prefix="/prompt-test", tags=["prompt-test"])


def _get_task_or_404(db: Session, task_id: int) -> PromptTestTask:
    task = db.get(PromptTestTask, task_id)
    if not task or task.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="测试任务不存在"
        )
    return task


def _get_unit_or_404(db: Session, unit_id: int) -> PromptTestUnit:
    stmt = (
        select(PromptTestUnit)
        .where(PromptTestUnit.id == unit_id)
        .options(selectinload(PromptTestUnit.task))
    )
    unit = db.execute(stmt).scalar_one_or_none()
    if not unit or (unit.task and unit.task.is_deleted):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="测试单元不存在"
        )
    return unit


def _validate_single_prompt_scope(
    db: Session, prompt_version_ids: Sequence[int | None]
) -> None:
    """确保一个测试任务只引用同一个 Prompt 下的版本。"""

    version_ids = [item for item in prompt_version_ids if item is not None]
    if not version_ids:
        return

    unique_ids = list(dict.fromkeys(version_ids))
    versions = db.scalars(
        select(PromptVersion).where(PromptVersion.id.in_(unique_ids))
    ).all()
    found_ids = {version.id for version in versions}
    missing_ids = [
        version_id for version_id in unique_ids if version_id not in found_ids
    ]
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prompt 版本不存在: {missing_ids}",
        )

    prompt_ids = {version.prompt_id for version in versions}
    if len(prompt_ids) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="同一个测试任务只能引用同一个 Prompt 下的版本",
        )


@router.get("/tasks", response_model=list[PromptTestTaskRead])
def list_prompt_test_tasks(
    *,
    db: Session = Depends(get_db),
    status_filter: PromptTestTaskStatus | None = Query(default=None, alias="status"),
) -> Sequence[PromptTestTask]:
    """按状态筛选测试任务列表。"""

    stmt = (
        select(PromptTestTask)
        .options(selectinload(PromptTestTask.units))
        .where(PromptTestTask.is_deleted.is_(False))
        .order_by(PromptTestTask.created_at.desc())
    )
    if status_filter:
        stmt = stmt.where(PromptTestTask.status == status_filter)
    return list(db.scalars(stmt))


@router.post(
    "/tasks", response_model=PromptTestTaskRead, status_code=status.HTTP_201_CREATED
)
def create_prompt_test_task(
    *, db: Session = Depends(get_db), payload: PromptTestTaskCreate
) -> PromptTestTask:
    """创建新的测试任务，可同时定义最小测试单元。"""

    units_payload = payload.units or []
    _validate_single_prompt_scope(
        db,
        [
            payload.prompt_version_id,
            *(unit_payload.prompt_version_id for unit_payload in units_payload),
        ],
    )

    task_data = payload.model_dump(exclude={"units", "auto_execute"})
    task = PromptTestTask(**task_data)
    db.add(task)
    db.flush()

    for unit_payload in units_payload:
        unit_data = unit_payload.model_dump(exclude_none=True)
        unit_data["task_id"] = task.id
        unit = PromptTestUnit(**unit_data)
        db.add(unit)

    if payload.auto_execute:
        task.status = PromptTestTaskStatus.READY

    db.commit()
    db.refresh(task)

    if payload.auto_execute:
        enqueue_prompt_test_task(task.id)

    return task


@router.post(
    "/tasks/{task_id}/ai-scoring",
    response_model=PromptTestAIScoreSummaryRead,
)
def run_ai_scoring_for_task(
    *,
    db: Session = Depends(get_db),
    task_id: int,
    payload: PromptTestAIScoringRequest,
) -> dict:
    """开启、补跑或重新执行测试任务 AI 评分。"""

    task = _get_task_or_404(db, task_id)
    scoring_config = AIScoringConfig(
        enabled=payload.enabled,
        evaluator_provider_id=payload.evaluator_provider_id,
        evaluator_model_id=payload.evaluator_model_id,
        evaluator_model_name=payload.evaluator_model_name,
        language=payload.language,
    )
    update_task_ai_scoring_status(task, scoring_config=scoring_config, status="running")
    db.commit()
    try:
        summary = score_task_outputs(
            db, task_id, force=payload.force, commit_progress=True
        )
    except PromptTestAIScoringError as exc:
        update_task_ai_scoring_status(
            task, scoring_config=scoring_config, status="failed", last_error=str(exc)
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    db.commit()
    return summary


@router.get(
    "/tasks/{task_id}/ai-scores",
    response_model=PromptTestAIScoreSummaryRead,
)
def get_ai_scores_for_task(*, db: Session = Depends(get_db), task_id: int) -> dict:
    """读取测试任务 AI 评分明细与汇总。"""

    _get_task_or_404(db, task_id)
    return build_task_score_summary(db, task_id)


@router.post(
    "/output-scores/{score_id}/retry",
    response_model=PromptTestOutputScoreRead,
)
def retry_ai_output_score(
    *, db: Session = Depends(get_db), score_id: int
) -> PromptTestOutputScore:
    """重试单条失败评分。"""

    score = db.get(PromptTestOutputScore, score_id)
    if score is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="评分记录不存在"
        )
    try:
        refreshed = retry_output_score(db, score)
    except PromptTestAIScoringError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    db.commit()
    db.refresh(refreshed)
    return refreshed


@router.post(
    "/tasks/{task_id}/optimization-recommendations",
    response_model=PromptTestOptimizationRecommendationRead,
)
def create_task_optimization_recommendation(
    *,
    db: Session = Depends(get_db),
    task_id: int,
    payload: PromptTestOptimizationRecommendationRequest,
) -> PromptTestOptimizationRecommendation:
    """基于 AI 评分生成测试任务优化建议。"""

    _get_task_or_404(db, task_id)
    try:
        recommendation = create_optimization_recommendation(
            db,
            task_id=task_id,
            prompt_version_id=payload.prompt_version_id,
            evaluator_provider_id=payload.evaluator_provider_id,
            evaluator_model_id=payload.evaluator_model_id,
            evaluator_model_name=payload.evaluator_model_name,
            language=payload.language,
        )
    except PromptTestAIScoringError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    db.commit()
    db.refresh(recommendation)
    return recommendation


@router.get(
    "/tasks/{task_id}/optimization-recommendations/latest",
    response_model=PromptTestOptimizationRecommendationRead | None,
)
def get_latest_task_optimization_recommendation(
    *,
    db: Session = Depends(get_db),
    task_id: int,
    prompt_version_id: int | None = Query(default=None),
) -> PromptTestOptimizationRecommendation | None:
    """读取测试任务最近一次优化建议。"""

    _get_task_or_404(db, task_id)
    return get_latest_recommendation(db, task_id, prompt_version_id=prompt_version_id)


@router.get(
    "/tasks/{task_id}/optimization-recommendations",
    response_model=list[PromptTestOptimizationRecommendationRead],
)
def list_task_optimization_recommendations(
    *,
    db: Session = Depends(get_db),
    task_id: int,
    prompt_version_id: int | None = Query(default=None),
) -> Sequence[PromptTestOptimizationRecommendation]:
    """读取测试任务优化建议历史。"""

    _get_task_or_404(db, task_id)
    return list_recommendations(db, task_id, prompt_version_id=prompt_version_id)


@router.get("/tasks/{task_id}", response_model=PromptTestTaskRead)
def get_prompt_test_task(
    *, db: Session = Depends(get_db), task_id: int
) -> PromptTestTask:
    """获取单个测试任务详情。"""

    task = _get_task_or_404(db, task_id)
    return task


@router.patch("/tasks/{task_id}", response_model=PromptTestTaskRead)
def update_prompt_test_task(
    *,
    db: Session = Depends(get_db),
    task_id: int,
    payload: PromptTestTaskUpdate,
) -> PromptTestTask:
    """更新测试任务的基础信息或状态。"""

    task = _get_task_or_404(db, task_id)

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)
    return task


@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_prompt_test_task(*, db: Session = Depends(get_db), task_id: int) -> Response:
    """将测试任务标记为删除，但保留历史数据。"""

    task = _get_task_or_404(db, task_id)
    if not task.is_deleted:
        task.is_deleted = True
        cancel_time = datetime.now(UTC)
        unfinished_experiments = db.scalars(
            select(PromptTestExperiment)
            .join(PromptTestUnit, PromptTestExperiment.unit_id == PromptTestUnit.id)
            .where(
                PromptTestUnit.task_id == task.id,
                PromptTestExperiment.status.in_(
                    [
                        PromptTestExperimentStatus.PENDING,
                        PromptTestExperimentStatus.RUNNING,
                    ]
                ),
            )
        )
        for experiment in unfinished_experiments:
            experiment.status = PromptTestExperimentStatus.CANCELLED
            experiment.error = experiment.error or "测试任务已取消"
            experiment.finished_at = cancel_time

        config = dict(task.config) if isinstance(task.config, dict) else {}
        config["last_error"] = "测试任务已取消"
        task.config = config
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/tasks/{task_id}/units", response_model=list[PromptTestUnitRead])
def list_units_for_task(
    *, db: Session = Depends(get_db), task_id: int
) -> Sequence[PromptTestUnit]:
    """列出指定测试任务下的全部最小测试单元。"""

    _get_task_or_404(db, task_id)

    stmt = (
        select(PromptTestUnit)
        .where(PromptTestUnit.task_id == task_id)
        .order_by(PromptTestUnit.created_at.asc())
    )
    return list(db.scalars(stmt))


@router.post(
    "/tasks/{task_id}/units",
    response_model=PromptTestUnitRead,
    status_code=status.HTTP_201_CREATED,
)
def create_unit_for_task(
    *,
    db: Session = Depends(get_db),
    task_id: int,
    payload: PromptTestUnitCreate,
) -> PromptTestUnit:
    """为指定测试任务新增最小测试单元。"""

    task = _get_task_or_404(db, task_id)
    existing_unit_version_ids = db.scalars(
        select(PromptTestUnit.prompt_version_id).where(
            PromptTestUnit.task_id == task_id
        )
    ).all()
    _validate_single_prompt_scope(
        db,
        [
            task.prompt_version_id,
            *existing_unit_version_ids,
            payload.prompt_version_id,
        ],
    )

    unit_data = payload.model_dump(exclude_none=True)
    unit_data["task_id"] = task_id
    unit = PromptTestUnit(**unit_data)
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


@router.get("/units/{unit_id}", response_model=PromptTestUnitRead)
def get_prompt_test_unit(
    *, db: Session = Depends(get_db), unit_id: int
) -> PromptTestUnit:
    """获取最小测试单元详情。"""

    unit = _get_unit_or_404(db, unit_id)
    return unit


@router.patch("/units/{unit_id}", response_model=PromptTestUnitRead)
def update_prompt_test_unit(
    *,
    db: Session = Depends(get_db),
    unit_id: int,
    payload: PromptTestUnitUpdate,
) -> PromptTestUnit:
    """更新最小测试单元配置。"""

    unit = _get_unit_or_404(db, unit_id)

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(unit, key, value)

    db.commit()
    db.refresh(unit)
    return unit


@router.get(
    "/units/{unit_id}/experiments", response_model=list[PromptTestExperimentRead]
)
def list_experiments_for_unit(
    *, db: Session = Depends(get_db), unit_id: int
) -> Sequence[PromptTestExperiment]:
    """列出指定测试单元下的实验记录。"""

    unit = _get_unit_or_404(db, unit_id)

    stmt = (
        select(PromptTestExperiment)
        .where(PromptTestExperiment.unit_id == unit.id)
        .order_by(PromptTestExperiment.created_at.desc())
    )
    return list(db.scalars(stmt))


@router.post(
    "/units/{unit_id}/experiments",
    response_model=PromptTestExperimentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_experiment_for_unit(
    *,
    db: Session = Depends(get_db),
    unit_id: int,
    payload: PromptTestExperimentCreate,
) -> PromptTestExperiment:
    """为指定测试单元创建实验，可选择立即执行。"""

    unit = _get_unit_or_404(db, unit_id)

    sequence = payload.sequence
    if sequence is None:
        sequence = (
            db.scalar(
                select(func.max(PromptTestExperiment.sequence)).where(
                    PromptTestExperiment.unit_id == unit.id
                )
            )
            or 0
        ) + 1

    experiment_data = payload.model_dump(exclude={"auto_execute"}, exclude_none=True)
    experiment_data["unit_id"] = unit.id
    experiment_data["sequence"] = sequence

    experiment = PromptTestExperiment(**experiment_data)
    db.add(experiment)
    db.flush()

    if payload.auto_execute:
        try:
            execute_prompt_test_experiment(db, experiment)
        except PromptTestExecutionError as exc:
            experiment.status = PromptTestExperimentStatus.FAILED
            experiment.error = str(exc)
            experiment.finished_at = datetime.now(UTC)
            db.flush()

    db.commit()
    db.refresh(experiment)
    return experiment


@router.get("/experiments/{experiment_id}", response_model=PromptTestExperimentRead)
def get_prompt_test_experiment(
    *, db: Session = Depends(get_db), experiment_id: int
) -> PromptTestExperiment:
    """获取实验结果详情。"""

    stmt = (
        select(PromptTestExperiment)
        .where(PromptTestExperiment.id == experiment_id)
        .options(
            selectinload(PromptTestExperiment.unit).selectinload(PromptTestUnit.task)
        )
    )
    experiment = db.execute(stmt).scalar_one_or_none()
    if not experiment or experiment.unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="实验记录不存在"
        )
    if experiment.unit.task and experiment.unit.task.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="实验记录不存在"
        )
    return experiment


@router.post(
    "/experiments/{experiment_id}/execute",
    response_model=PromptTestExperimentRead,
)
def execute_existing_experiment(
    *, db: Session = Depends(get_db), experiment_id: int
) -> PromptTestExperiment:
    """重新执行已存在的实验记录。"""

    stmt = (
        select(PromptTestExperiment)
        .where(PromptTestExperiment.id == experiment_id)
        .options(
            selectinload(PromptTestExperiment.unit).selectinload(PromptTestUnit.task)
        )
    )
    experiment = db.execute(stmt).scalar_one_or_none()
    if not experiment or experiment.unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="实验记录不存在"
        )
    if experiment.unit.task and experiment.unit.task.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="实验记录不存在"
        )

    try:
        execute_prompt_test_experiment(db, experiment)
    except PromptTestExecutionError as exc:
        experiment.status = PromptTestExperimentStatus.FAILED
        experiment.error = str(exc)
        experiment.finished_at = datetime.now(UTC)

    db.commit()
    db.refresh(experiment)
    return experiment


__all__ = ["router"]
