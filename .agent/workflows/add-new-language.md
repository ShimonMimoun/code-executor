---
description: Add a New Supported Language to the Sandbox
---
# Add a New Language

Adding a new programming language involves extending the Docker sandbox image and updating the API data models to recognize it.

## 1. Update the Sandbox Dockerfile
The sandbox is a single Docker image containing runtimes for all supported languages.
File: `sandbox/Dockerfile`

1. Find the appropriate base installation block or add a new one.
2. Use package managers (`apt`, `npm`, `pip`, etc.) to install the runtime (e.g., `apt-get install -y ruby`).
3. Ensure it runs smoothly under a non-root environment if possible.

## 2. Create the Sandbox Execution Script
Each language has a lightweight bash execution script inside the sandbox image. This handles extracting code, installing optional dependencies, and invoking the compiler/interpreter.
File: `sandbox/scripts/run_<language>.sh`

1. Create a new file (e.g. `sandbox/scripts/run_ruby.sh`).
2. The script typically receives user code in `/tmp/code.<ext>`.
3. Provide instructions on handling dependencies (if supported) and managing standard input (`< /dev/stdin`).
4. Ensure you reference this new script in the `Dockerfile` COPY command and make it executable (`chmod +x`).

## 3. Update the API Models
The API must be aware of the new language to pass validation and route requests properly.
File: `backend/app/models.py`

1. Modify `ExecutionRequest.language` field description to list the new language.
2. Create or update the backend configuration (`backend/config.toml` or `config.example.toml`) to include the language in the supported mapping, determining its extension, default version, etc.

## 4. Rebuild the Sandbox Image
Because the sandbox environment changed, you must rebuild it locally to test.

```bash
docker build -t code-executor-sandbox:latest ./sandbox/
```

## 5. (Optional) Update the Frontend
If the frontend provides syntax highlighting, ensure Monaco Editor recognizes the new language snippet.
File: `frontend/src/` (Check language dropdowns or editor configurations).
