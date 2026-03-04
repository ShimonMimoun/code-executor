"""Execution API routes."""

import uuid
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.auth import verify_api_key
from app.config import settings
from app.models import (
    ExecutionRequest,
    ExecutionResponse,
    ExecutionListItem,
    ExecutionStatus,
    LanguageInfo,
)
from app.services.queue import execution_queue
from app.services.sandbox import sandbox_manager, LANGUAGE_CONFIG

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Execution"])


async def _run_execution(execution_id: str, request: ExecutionRequest):
    """Background task: execute code in sandbox and store results."""
    await execution_queue.update_execution(execution_id, ExecutionStatus.RUNNING)

    result = await sandbox_manager.execute_code(
        execution_id=execution_id,
        code=request.code,
        language=request.language,
        version=request.version,
        stdin=request.stdin,
        timeout=request.timeout,
        memory_limit=request.memory_limit,
        dependencies=request.dependencies,
    )

    await execution_queue.update_execution(
        execution_id=execution_id,
        status=result["status"],
        stdout=result["stdout"],
        stderr=result["stderr"],
        exit_code=result["exit_code"],
        execution_time_ms=result["execution_time_ms"],
    )
    logger.info(
        "Execution %s completed: status=%s, time=%.1fms",
        execution_id, result["status"], result["execution_time_ms"],
    )


@router.post(
    "/execute",
    response_model=ExecutionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit code for execution",
    description="Submits code to be executed in an isolated sandbox container. Returns immediately with an execution ID.",
)
async def execute_code(
    request: ExecutionRequest,
    background_tasks: BackgroundTasks,
    _api_key: str = Depends(verify_api_key),
):
    if request.language not in settings.supported_languages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language: {request.language}. Supported: {settings.supported_languages}",
        )

    execution_id = str(uuid.uuid4())
    response = await execution_queue.create_execution(execution_id, request.language)
    background_tasks.add_task(_run_execution, execution_id, request)
    return response


@router.post(
    "/execute/sync",
    response_model=ExecutionResponse,
    summary="Execute code synchronously",
    description="Executes code and waits for the result. Useful for short-running scripts.",
)
async def execute_code_sync(
    request: ExecutionRequest,
    _api_key: str = Depends(verify_api_key),
):
    if request.language not in settings.supported_languages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language: {request.language}. Supported: {settings.supported_languages}",
        )

    execution_id = str(uuid.uuid4())
    await execution_queue.create_execution(execution_id, request.language)
    await execution_queue.update_execution(execution_id, ExecutionStatus.RUNNING)

    result = await sandbox_manager.execute_code(
        execution_id=execution_id,
        code=request.code,
        language=request.language,
        version=request.version,
        stdin=request.stdin,
        timeout=request.timeout,
        memory_limit=request.memory_limit,
        dependencies=request.dependencies,
    )

    await execution_queue.update_execution(
        execution_id=execution_id,
        status=result["status"],
        stdout=result["stdout"],
        stderr=result["stderr"],
        exit_code=result["exit_code"],
        execution_time_ms=result["execution_time_ms"],
    )

    final = await execution_queue.get_execution(execution_id)
    return final


@router.get(
    "/executions/{execution_id}",
    response_model=ExecutionResponse,
    summary="Get execution result",
)
async def get_execution(
    execution_id: str,
    _api_key: str = Depends(verify_api_key),
):
    result = await execution_queue.get_execution(execution_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {execution_id} not found or expired.",
        )
    return result


@router.get(
    "/executions",
    response_model=list[ExecutionListItem],
    summary="List recent executions",
)
async def list_executions(
    limit: int = 20,
    _api_key: str = Depends(verify_api_key),
):
    return await execution_queue.list_executions(limit=min(limit, 100))


@router.get(
    "/languages",
    response_model=list[LanguageInfo],
    summary="List supported languages with versions",
)
async def list_languages():
    """Returns the list of supported programming languages and their versions."""
    return [
        LanguageInfo(
            name=name,
            display=config["display"],
            version=config["version"],
            versions=config["versions"],
            file_extension=config["extension"],
            example=config["example"],
            output_type=config.get("output_type", "text"),
        )
        for name, config in LANGUAGE_CONFIG.items()
        if name in settings.supported_languages
    ]
