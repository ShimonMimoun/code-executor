#!/bin/bash
# Pre-commit hook installer

HOOK_DIR=".git/hooks"
HOOK_FILE="${HOOK_DIR}/pre-commit"

if [ ! -d ".git" ]; then
    echo "Error: Not a git repository. Run this from the root."
    exit 1
fi

echo "Installing pre-commit hook..."

cat << 'EOF' > "$HOOK_FILE"
#!/bin/bash

# Pre-commit validation hook

echo "🚀 Running Code Executor Pre-Commit Validation..."

# 1. Backend Python Checks
if [ -d "backend" ]; then
    echo "🐍 Checking Backend (Python)..."
    cd backend
    if command -v uv &> /dev/null; then
        uv run ruff check . || exit 1
        uv run ruff format --check . || exit 1
    else
        echo "⚠️  'uv' not found. Skipping python linting."
    fi
    cd ..
fi

# 2. Frontend Node Checks
if [ -d "frontend" ]; then
    echo "⚛️  Checking Frontend (React)..."
    cd frontend
    if [ -f "package.json" ]; then
        npm run lint || exit 1
    fi
    cd ..
fi

echo "✅ All checks passed! Ready to commit."
EOF

chmod +x "$HOOK_FILE"
echo "✅ Hook installed successfully at $HOOK_FILE"
