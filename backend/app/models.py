"""Pydantic models for API requests and responses."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    """Status of a code execution."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ExecutionRequest(BaseModel):
    """Request body to submit code for execution."""

    code: str = Field(..., description="Source code to execute", min_length=1, max_length=50_000)
    language: str = Field(..., description="Programming language (python, javascript, go, bash, java, csharp, html, react)")
    version: Optional[str] = Field(None, description="Language version (e.g. '3.12' for Python, '22' for Node.js). Uses default if omitted.")
    stdin: Optional[str] = Field(None, description="Standard input to provide to the program")
    timeout: Optional[int] = Field(None, ge=1, le=120, description="Max execution time in seconds")
    memory_limit: Optional[str] = Field(None, description="Memory limit (e.g. '256m', '512m')")
    dependencies: Optional[List[str]] = Field(
        None,
        description="List of packages to install before execution (e.g. ['requests', 'numpy'] for Python, ['lodash', 'axios'] for JS)",
        max_length=20,
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": 'import requests\nprint(requests.get("https://httpbin.org/ip").json())',
                    "language": "python",
                    "dependencies": ["requests"],
                    "timeout": 30,
                }
            ]
        }
    }


class ExecutionResponse(BaseModel):
    """Response after submitting or querying an execution."""

    execution_id: str
    status: ExecutionStatus
    language: str
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    exit_code: Optional[int] = None
    execution_time_ms: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class ExecutionListItem(BaseModel):
    """Lightweight execution summary for listing."""

    execution_id: str
    status: ExecutionStatus
    language: str
    created_at: datetime
    execution_time_ms: Optional[float] = None


class LanguageInfo(BaseModel):
    """Information about a supported language."""

    name: str
    display: str
    version: str
    versions: List[str]
    file_extension: str
    example: str
    output_type: str = "text"


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    redis: str
    docker: str
