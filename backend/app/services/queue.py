"""Execution queue and result store with in-memory fallback when Redis is unavailable."""

import json
import logging
from collections import OrderedDict
from datetime import datetime
from typing import Optional, List

from app.config import settings
from app.models import ExecutionResponse, ExecutionStatus, ExecutionListItem

logger = logging.getLogger(__name__)

# Redis key prefixes
EXEC_PREFIX = "exec:"
QUEUE_KEY = "exec:queue"
HISTORY_KEY = "exec:history"


class InMemoryStore:
    """Simple in-memory fallback when Redis is not available."""

    def __init__(self, max_size: int = 100):
        self._data: OrderedDict[str, dict] = OrderedDict()
        self._max_size = max_size

    def set(self, key: str, value: str):
        if len(self._data) >= self._max_size:
            self._data.popitem(last=False)
        self._data[key] = value

    def get(self, key: str) -> Optional[str]:
        return self._data.get(key)

    def history(self, limit: int) -> list:
        keys = list(reversed(list(self._data.keys())))[:limit]
        return keys


class ExecutionQueue:
    """Manages execution state and results. Uses Redis if available, in-memory otherwise."""

    def __init__(self):
        self._redis = None
        self._use_redis = False
        self._memory_store = InMemoryStore()
        self._history: list[str] = []

    async def connect(self):
        """Try to connect to Redis; fall back to in-memory if unavailable."""
        try:
            import redis.asyncio as redis_lib

            self._redis = redis_lib.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._redis.ping()
            self._use_redis = True
            logger.info("✅ Connected to Redis at %s", settings.redis_url)
        except Exception as e:
            logger.warning("⚠️  Redis unavailable (%s) — using in-memory store", e)
            self._use_redis = False
            self._redis = None

    async def disconnect(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    async def is_healthy(self) -> bool:
        """Check connectivity."""
        if self._use_redis:
            try:
                await self._redis.ping()
                return True
            except Exception:
                return False
        return True  # in-memory is always healthy

    async def _store_set(self, key: str, value: str):
        if self._use_redis:
            await self._redis.set(key, value, ex=settings.result_ttl_seconds)
        else:
            self._memory_store.set(key, value)

    async def _store_get(self, key: str) -> Optional[str]:
        if self._use_redis:
            return await self._redis.get(key)
        return self._memory_store.get(key)

    async def create_execution(
        self, execution_id: str, language: str
    ) -> ExecutionResponse:
        """Create a new execution record with QUEUED status."""
        now = datetime.utcnow()
        data = {
            "execution_id": execution_id,
            "status": ExecutionStatus.QUEUED.value,
            "language": language,
            "stdout": None,
            "stderr": None,
            "exit_code": None,
            "execution_time_ms": None,
            "created_at": now.isoformat(),
            "completed_at": None,
        }
        key = f"{EXEC_PREFIX}{execution_id}"
        await self._store_set(key, json.dumps(data))

        # Track history
        if self._use_redis:
            await self._redis.lpush(HISTORY_KEY, execution_id)
            await self._redis.ltrim(HISTORY_KEY, 0, 99)
        else:
            self._history.insert(0, execution_id)
            self._history = self._history[:100]

        return ExecutionResponse(
            execution_id=execution_id,
            status=ExecutionStatus.QUEUED,
            language=language,
            created_at=now,
        )

    async def update_execution(
        self,
        execution_id: str,
        status: ExecutionStatus,
        stdout: Optional[str] = None,
        stderr: Optional[str] = None,
        exit_code: Optional[int] = None,
        execution_time_ms: Optional[float] = None,
    ):
        """Update an execution record with results."""
        key = f"{EXEC_PREFIX}{execution_id}"
        raw = await self._store_get(key)
        if not raw:
            logger.warning("Execution %s not found", execution_id)
            return

        data = json.loads(raw)
        data["status"] = status.value
        data["stdout"] = stdout
        data["stderr"] = stderr
        data["exit_code"] = exit_code
        data["execution_time_ms"] = execution_time_ms
        if status in (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT):
            data["completed_at"] = datetime.utcnow().isoformat()

        await self._store_set(key, json.dumps(data))

    async def get_execution(self, execution_id: str) -> Optional[ExecutionResponse]:
        """Retrieve an execution record by ID."""
        key = f"{EXEC_PREFIX}{execution_id}"
        raw = await self._store_get(key)
        if not raw:
            return None
        data = json.loads(raw)
        return ExecutionResponse(
            execution_id=data["execution_id"],
            status=ExecutionStatus(data["status"]),
            language=data["language"],
            stdout=data.get("stdout"),
            stderr=data.get("stderr"),
            exit_code=data.get("exit_code"),
            execution_time_ms=data.get("execution_time_ms"),
            created_at=datetime.fromisoformat(data["created_at"]),
            completed_at=(
                datetime.fromisoformat(data["completed_at"])
                if data.get("completed_at")
                else None
            ),
        )

    async def list_executions(self, limit: int = 20) -> List[ExecutionListItem]:
        """List recent executions."""
        if self._use_redis:
            ids = await self._redis.lrange(HISTORY_KEY, 0, limit - 1)
        else:
            ids = self._history[:limit]

        items = []
        for exec_id in ids:
            key = f"{EXEC_PREFIX}{exec_id}"
            raw = await self._store_get(key)
            if raw:
                data = json.loads(raw)
                items.append(
                    ExecutionListItem(
                        execution_id=data["execution_id"],
                        status=ExecutionStatus(data["status"]),
                        language=data["language"],
                        created_at=datetime.fromisoformat(data["created_at"]),
                        execution_time_ms=data.get("execution_time_ms"),
                    )
                )
        return items


# Singleton instance
execution_queue = ExecutionQueue()
