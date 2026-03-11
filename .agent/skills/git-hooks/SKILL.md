---
name: Git Hooks & Validation
description: Utility to manage, trigger, and enforce local Git hooks and code formatting.
---

# Git Hooks Skill

This skill provides agents and developers with a simple mechanism to validate code quality before committing changes. It leverages pre-commit hooks to ensure the Python backend, React frontend, and infrastructure files meet the repository's styling standards.

## Usage Guide for Agents

Before an AI agent executes a `git commit` or creates a Pull Request, it **should** run the quality checks.

### 1. Manual Validation Script
You can use the provided `run_hooks.sh` script to trigger formatters and linters on the codebase.

```bash
# Run tests and linters
bash .agent/skills/git-hooks/run_hooks.sh
```

### 2. Available Formatters
The following tools should be respected by the agent when writing code:

- **Backend (Python)**: `uv run ruff check` and `uv run ruff format`
- **Frontend (Node/React)**: `npm run lint` and `npm run format` (using ESLint/Prettier)
- **Helm/YAML**: Standard YAML linters.

## Setting up Native Git Hooks
To ensure developers also adhere to these rules automatically upon `git commit`, the agent can install the hooks native into `.git/hooks/pre-commit`.

```bash
# Install the pre-commit hook
bash .agent/skills/git-hooks/install.sh
```
