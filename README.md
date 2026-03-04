# Code Executor Platform

> 🚀 Secure code execution platform for AI agents — run arbitrary code in isolated Docker sandbox containers.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  Clients (AI Agents / React Dashboard)               │
└──────────────┬───────────────────────────────────────┘
               │ REST API + WebSocket
┌──────────────▼───────────────────────────────────────┐
│  FastAPI Server                                       │
│  ├── Authentication (X-API-Key)                       │
│  ├── /api/v1/execute        → Submit code             │
│  ├── /api/v1/execute/sync   → Execute & wait          │
│  ├── /api/v1/executions/:id → Get result              │
│  ├── /api/v1/languages      → List languages          │
│  └── /health, /ready        → Probes                  │
└──────────────┬───────────────────────────────────────┘
               │
  ┌────────────▼──────┐    ┌──────────────────────┐
  │  Redis             │    │  Docker Sandbox      │
  │  (Queue + Results) │    │  (Ephemeral, Locked) │
  └───────────────────┘    │  ├── Python 3.12      │
                           │  ├── Node.js 22       │
                           │  ├── Go 1.22          │
                           │  ├── Java 21          │
                           │  ├── C# 8.0           │
                           │  └── Bash 5           │
                           └──────────────────────┘
```

## Execution Capabilities

The sandbox natively supports the following languages. Additionally, the platform provides automatic fallback to local subprocess execution if Docker isn't available.

| Language | Versions | Default | Dependencies |
| :--- | :--- | :--- | :--- |
| **Python** | 3.9, 3.10, 3.11, 3.12, 3.13 | 3.12 | `pip install` |
| **Node.js** | 18, 19, 20, 21, 22, 23, 24 | 22 | `npm install` |
| **Go** | 1.20, 1.21, 1.22, 1.23 | 1.22 | `go mod init && go get` |
| **Java** | 17, 21, 22, 23 | 21 | Maven `dependency:copy-dependencies` |
| **C#** | 8.0, 9.0 | 8.0 | `dotnet add package` |
| **Bash** | 5 | 5 | N/A |
| **HTML/CSS/JS**| 5 | 5 | N/A (Frontend WebView rendering) |
| **React** | 18, 19 | 19 | N/A (Frontend React+Babel injection) |

---

## Model Context Protocol (MCP) Server

To use this platform as a tool backend for an AI Agent via the [Model Context Protocol](https://modelcontextprotocol.github.io/), use the provided MCP server. This allows any MCP-compatible AI (like Claude Desktop) to write and execute code natively.

1. Compile the server:
   ```bash
   cd mcp-server
   npm install
   npm run build
   ```
2. Configure your AI client (e.g. `claude_desktop_config.json`):
   ```json
   {
     "mcpServers": {
       "code-executor": {
         "command": "node",
         "args": ["/absolute/path/to/mcp-server/build/index.js"],
         "env": {
           "CODE_EXECUTOR_API_URL": "http://localhost:8000",
           "CODE_EXECUTOR_API_KEY": "dev-api-key-change-me"
         }
       }
     }
   }
   ```

## Quick Start

### 1. Configure the Environment
Ensure you create your backend configuration locally before spinning up.
A default configuration can be found in `backend/config.example.toml`. Copy this entirely and rename it to `backend/config.toml`:

```bash
cp backend/config.example.toml backend/config.toml
```

### 2. Build the sandbox image

```bash
docker build -t code-executor-sandbox:latest ./sandbox/
```

### 3. Start all services

```bash
docker compose up -d
```

### 4. Test it

```bash
curl -X POST http://localhost:8000/api/v1/execute/sync \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-change-me" \
  -d '{"code": "print(\"Hello from sandbox!\")", "language": "python"}'
```

### 5. Open the dashboard

Visit [http://localhost:3000](http://localhost:3000)

## Development

### Backend only (using `uv`)

```bash
cd backend
uv install
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend only

```bash
cd frontend
npm install
npm run dev
```

## API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/v1/execute` | ✅ | Submit code (async) |
| `POST` | `/api/v1/execute/sync` | ✅ | Execute & wait |
| `GET` | `/api/v1/executions/{id}` | ✅ | Get result |
| `GET` | `/api/v1/executions` | ✅ | List recent |
| `GET` | `/api/v1/languages` | ❌ | List languages |
| `GET` | `/health` | ❌ | Health check |
| `GET` | `/ready` | ❌ | Readiness probe |

### Execute Request Body

```json
{
  "code": "print('hello')",
  "language": "python",
  "stdin": "optional input",
  "timeout": 30,
  "memory_limit": "256m"
}
```

### Execute Response

```json
{
  "execution_id": "uuid",
  "status": "completed",
  "language": "python",
  "stdout": "hello\n",
  "stderr": "",
  "exit_code": 0,
  "execution_time_ms": 142.5,
  "created_at": "2026-03-04T21:00:00Z",
  "completed_at": "2026-03-04T21:00:00Z"
}
```

## Security

Each execution runs in a Docker container with:

- **No network** (`--network=none`)
- **Read-only filesystem** (`--read-only`, writable `/tmp` only)
- **All capabilities dropped** (`--cap-drop=ALL`)
- **Non-root user** (UID 1000)
- **Memory limit** (256MB default)
- **CPU limit** (1 core)
- **PID limit** (64 processes)
- **No privilege escalation** (`--security-opt no-new-privileges`)
- **Ephemeral** — container destroyed after each execution

## Kubernetes / OpenShift Deployment

We provide a bundled generic Helm chart to deploy the entire stack—API, Redis internal queue, and React dashboard—into any Kubernetes or OpenShift cluster.

```bash
# Review default values and customize if needed
cat helm/code-executor/values.yaml

# Create the namespace
kubectl create namespace code-executor
kubectl config set-context --current --namespace=code-executor

# Deploy the Helm chart
helm install code-executor ./helm/code-executor/

# (Optional) OpenShift specific: Expose the API route manually if route.enabled=false
oc expose svc/code-executor-api
```

By default:
- **Redis** is spun up alongside the API (`redis.enabled: true`).
- **Frontend** dashboard is included (`frontend.enabled: true`).
- **API configuration** is dynamically mapped via `config` block in `values.yaml`.

## Tech Stack

- **Backend**: FastAPI, Python 3.12, Redis, Docker SDK, `uv` (Package Manager), TOML
- **Frontend**: React 19, Vite, Monaco Editor
- **Sandbox**: Python, Node.js, Go, Java, C#, Bash, HTML, React
- **Integration**: MCP (Model Context Protocol) Server
- **DevOps**: Docker Compose, OpenShift

## License

MIT
