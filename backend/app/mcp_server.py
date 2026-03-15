"""MCP server exposing code execution capabilities."""

import logging
import uuid
from typing import Optional

import mcp.types as types
from mcp.server import Server

from app.services.sandbox import sandbox_manager
from app.services.queue import execution_queue
from app.models import ExecutionStatus

logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp_server = Server("code-executor")

@mcp_server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="execute_code",
            description="Execute code in an isolated sandbox container.",
            inputSchema={
                "type": "object",
                "properties": {
                    "language": {
                        "type": "string",
                        "description": "Programming language (e.g., python, bash)"
                    },
                    "code": {
                        "type": "string",
                        "description": "The source code to execute"
                    },
                    "version": {
                        "type": "string",
                        "description": "Language version (default '*')",
                        "default": "*"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default 15)",
                        "default": 15
                    }
                },
                "required": ["language", "code"]
            }
        )
    ]

@mcp_server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name != "execute_code":
        raise ValueError(f"Unknown tool: {name}")

    if not arguments:
        arguments = {}

    language = arguments.get("language")
    code = arguments.get("code")
    version = arguments.get("version", "*")
    timeout = arguments.get("timeout", 15)

    if not language or not code:
        raise ValueError("Missing 'language' or 'code' arguments")

    logger.info("MCP hit: execute_code in %s language", language)
    execution_id = str(uuid.uuid4())
    
    # We create an entry in the local executing queue just in case someone looks at the main platform dashboard
    await execution_queue.create_execution(execution_id, language)
    await execution_queue.update_execution(execution_id, ExecutionStatus.RUNNING)

    result = await sandbox_manager.execute_code(
        execution_id=execution_id,
        code=code,
        language=language,
        version=version,
        stdin="",
        timeout=timeout,
        memory_limit=256,
        dependencies={},
    )

    await execution_queue.update_execution(
        execution_id=execution_id,
        status=result["status"],
        stdout=result["stdout"],
        stderr=result["stderr"],
        exit_code=result["exit_code"],
        execution_time_ms=result["execution_time_ms"],
    )

    # Return output (stdout + stderr or exit info)
    out = ""
    if result["stdout"]:
        out += result["stdout"]
    if result["stderr"]:
        if out:
            out += "\n"
        out += f"--- STDERR ---\n{result['stderr']}"
    
    if result["status"] != ExecutionStatus.COMPLETED:
        out += f"\n--- Execution finished with status: {result['status'].value} (code: {result['exit_code']}) ---"

    if not out:
        out = "Execution completed with no output."
        
    return [types.TextContent(type="text", text=out)]

