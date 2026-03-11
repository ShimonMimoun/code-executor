---
name: Test Executions API
description: Easily trigger and wait for code executions against the backend API during development.
---

# Test Executions API Skill

This skill provides a simple python script to interact with the Code Executor backend API. It abstracts away formulating verbose `curl` commands for execution testing.

## Usage

When testing the backend, use the `test_execution.py` script provided in this directory.

1. Ensure the platform API is running locally (usually at `http://localhost:8000`).
2. Run the script using the local python environment or `uv`.

```bash
# Basic python execution
python .agent/skills/test-api/test_execution.py

# Execute specific language and code
python .agent/skills/test-api/test_execution.py --lang javascript --code 'console.log("hello Node.js");'

# Use specific version
python .agent/skills/test-api/test_execution.py --lang go --code 'package main; import "fmt"; func main() { fmt.Println("Hello Go") }'
```

For advanced testing scenarios (like submitting multiple requests concurrently or testing error handling), modify or duplicate the `test_execution.py` script.
