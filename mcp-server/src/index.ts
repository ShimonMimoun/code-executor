import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
    CallToolRequestSchema,
    ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import axios from "axios";

const API_URL = process.env.CODE_EXECUTOR_API_URL || "http://localhost:8000";
const API_KEY = process.env.CODE_EXECUTOR_API_KEY || "dev-api-key-change-me";

const server = new Server(
    {
        name: "code-executor",
        version: "1.0.0",
    },
    {
        capabilities: {
            tools: {},
        },
    }
);

const axiosInstance = axios.create({
    baseURL: API_URL,
    headers: {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
    },
});

server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
        tools: [
            {
                name: "list_supported_languages",
                description: "List all supported programming languages and their available versions for code execution.",
                inputSchema: {
                    type: "object",
                    properties: {},
                },
            },
            {
                name: "execute_code",
                description: "Execute arbitrary code in an isolated sandbox environment. Used to run scripts, solve math problems, process text, run servers, etc.",
                inputSchema: {
                    type: "object",
                    properties: {
                        language: {
                            type: "string",
                            description: "The programming language (e.g., 'python', 'javascript', 'go', 'bash', 'java', 'csharp', 'html', 'react')",
                        },
                        code: {
                            type: "string",
                            description: "The source code to execute",
                        },
                        version: {
                            type: "string",
                            description: "Optional version to use (e.g. '3.12' for Python)",
                        },
                        dependencies: {
                            type: "array",
                            items: { type: "string" },
                            description: "Optional list of external dependencies to install (e.g. ['requests', 'pandas'] for Python, ['lodash'] for JS, ['github.com/google/uuid'] for Go)",
                        },
                        timeout: {
                            type: "number",
                            description: "Optional execution timeout in seconds (default is 30)",
                        },
                        stdin: {
                            type: "string",
                            description: "Optional standard input to pass to the executed script",
                        }
                    },
                    required: ["language", "code"],
                },
            },
        ],
    };
});

server.setRequestHandler(CallToolRequestSchema, async (request: any) => {
    const { name, arguments: args } = request.params;

    try {
        if (name === "list_supported_languages") {
            const response = await axiosInstance.get("/api/v1/languages");
            return {
                content: [{ type: "text", text: JSON.stringify(response.data, null, 2) }],
            };
        } else if (name === "execute_code") {
            const { language, code, version, dependencies, timeout, stdin } = args as Record<string, any>;

            const response = await axiosInstance.post("/api/v1/execute/sync", {
                language,
                code,
                version,
                dependencies,
                timeout,
                stdin,
            });

            const result = response.data;

            let textOutput = `Status: ${result.status}
Execution Time: ${result.execution_time_ms}ms
Exit Code: ${result.exit_code}`;

            if (result.stdout) {
                textOutput += `\n\n--- STDOUT ---\n${result.stdout}`;
            }
            if (result.stderr) {
                textOutput += `\n\n--- STDERR ---\n${result.stderr}`;
            }

            return {
                content: [{ type: "text", text: textOutput }],
                isError: result.status !== "completed",
            };
        }

        throw new Error(`Unknown tool: ${name}`);
    } catch (error: any) {
        if (error.response) {
            return {
                content: [{ type: "text", text: `API Request failed: ${JSON.stringify(error.response.data)}` }],
                isError: true,
            };
        }
        return {
            content: [{ type: "text", text: `Error: ${error.message}` }],
            isError: true,
        };
    }
});

async function main() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error("Code Executor MCP Server running on stdio");
}

main().catch(console.error);
