from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analysis_module import (
    AnalysisModuleDefinition,
    AnalysisResultPayload,
    ModuleExecutionRequest,
)
from app.services.analysis_runner import (
    AnalysisDataLoadError,
    AnalysisTaskNotFoundError,
    ParameterValidationError,
    RequirementValidationError,
    UnknownModuleError,
    execute_module_for_test_run,
    serialize_analysis_result,
)
from app.services.analysis_registry import get_analysis_registry


router = APIRouter()


@router.get("/modules", response_model=list[AnalysisModuleDefinition])
def list_analysis_modules() -> list[AnalysisModuleDefinition]:
    """列出当前可用的分析模块。"""

    registry = get_analysis_registry()
    return registry.list_definitions()


@router.post("/modules/execute", response_model=AnalysisResultPayload)
def run_analysis_module(
    request: ModuleExecutionRequest, db: Session = Depends(get_db)
) -> AnalysisResultPayload:
    """执行指定的分析模块并返回结果。"""

    try:
        result = execute_module_for_test_run(db, request)
    except UnknownModuleError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except AnalysisTaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ParameterValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    except RequirementValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except AnalysisDataLoadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return serialize_analysis_result(request.module_id, result)


__all__ = ["router"]
