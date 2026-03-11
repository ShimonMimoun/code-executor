---
name: Security Auditing and Guidelines
description: Guidelines and tools for security auditing.
---

# Security Skill

This document outlines the core security expectations for any code produced by AI agents or developers in the Code Executor repository.

## Agent Directives

1. **No Hardcoded Secrets**: Under no circumstances should API keys, database credentials, or secret tokens be hardcoded into the source code. Always use environment variables (e.g., `os.getenv()`, `process.env`).
2. **Input Validation**: The Code Executor API relies heavily on user-provided input (`code`, `stdin`). Ensure that validation logic remains strict on the FastAPI side (Pydantic lengths, types, etc.) before the payload reaches the sandbox Docker runtime.
3. **Sandbox Rigidity**: Do not modify `sandbox/Dockerfile` or backend execution logic in a way that weakens the container restrictions (e.g. giving it network access, mounting sensitive host volumes, running as root).
4. **Log Sanitization**: Ensure that logging frameworks do not inadvertently output secure keys.

## Automatic Auditing
Agents should periodically, or prior to significant merges, trigger the included security audit script to verify no known vulnerable dependencies were introduced into the project.

### Running the Audit
```bash
bash .agent/skills/security/audit.sh
```

This script will run:
- Node.js dependency vulnerability scans via `npm audit` in the `frontend/` directory.
- Python SAST (Static Application Security Testing) scanning via `bandit` in the `backend/` directory, leveraging the `uvx` runner.
