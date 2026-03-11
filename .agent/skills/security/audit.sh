#!/bin/bash
# Security Audit Tooling for AI Agents

echo "🔒 Starting Security Audit for Code Executor Platform"

# 1. Frontend Audit (npm dependencies)
if [ -d "frontend" ]; then
    echo "====================================="
    echo "🔍 Auditing Frontend (Node.js)..."
    cd frontend
    if [ -f "package.json" ]; then
        # Run audit but only fail on high/critical
        npm audit --audit-level=high
        if [ $? -ne 0 ]; then
            echo "❌ High/Critical vulnerabilities found in frontend dependencies."
            # We don't exit immediately to allow backend audit to run, but capture failure
            FRONTEND_FAIL=1
        else
            echo "✅ Frontend passed npm audit."
        fi
    fi
    cd ..
fi

# 2. Backend Audit (Python static analysis)
if [ -d "backend" ]; then
    echo "====================================="
    echo "🔍 Auditing Backend (Python via Bandit)..."
    cd backend
    if command -v uvx &> /dev/null || command -v uv &> /dev/null; then
        echo "Running bandit scanner..."
        # Use uv to run bandit locally without installing it permanently in the project deps
        # Exclude tests and virtual environments
        uvx bandit -r app/ -c pyproject.toml --skip B104 || uvx bandit -r app/
        if [ $? -ne 0 ]; then
            echo "❌ Bandit reported security issues in the backend."
            BACKEND_FAIL=1
        else
            echo "✅ Backend passed Bandit static analysis."
        fi
    else
        echo "⚠️  'uv' or 'uvx' not found. Skipping python security scanning."
    fi
    cd ..
fi

echo "====================================="
if [ "$FRONTEND_FAIL" = "1" ] || [ "$BACKEND_FAIL" = "1" ]; then
    echo "🚨 SECURITY AUDIT FAILED! Please review the logs above."
    exit 1
else
    echo "🎉 All Security Audits Passed successfully!"
    exit 0
fi
