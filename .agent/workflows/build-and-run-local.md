---
description: Build and Run Code Executor Locally
---
# Build and Run Local Development Environment

This workflow guides you through running the Code Executor stack locally for development or testing purposes. 

## Prerequisites
- Docker & Docker Compose
- Python 3.12+ and `uv` (for backend standalone)
- Node.js 22+ (for frontend standalone)

## 1. Using Docker Compose (Recommended)
This runs the entire stack: API, Redis, Frontend Dashboard, and the shared Docker daemon for the sandbox.

```bash
# Build the Docker sandbox image first
docker build -t code-executor-sandbox:latest ./sandbox/

# Create a local configuration from the example
cp backend/config.example.toml backend/config.toml

# Start all services detached
docker compose up -d
```
The API is at `http://localhost:8000` and Dashboard at `http://localhost:3000`.

## 2. Using Standalone Services
If you need to debug the backend or frontend directly on your host machine.

### Backend
```bash
cd backend
uv install
# Ensure you copy backend/config.example.toml to backend/config.toml first
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## 3. Testing It's Working
You can verify the components are connected using the sync API endpoint:
```bash
curl -X POST http://localhost:8000/api/v1/execute/sync \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-change-me" \
  -d '{"code": "print(\"Hello world\")", "language": "python"}'
```
