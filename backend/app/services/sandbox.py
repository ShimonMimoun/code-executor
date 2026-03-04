"""Sandbox manager — executes code in Docker containers or local subprocess fallback.

Supports multiple language versions and dependency installation.
"""

import asyncio
import logging
import os
import subprocess
import tempfile
import time
import shutil
from typing import AsyncGenerator, Optional

from app.config import settings
from app.models import ExecutionStatus

logger = logging.getLogger(__name__)

# ================================================================
# LANGUAGE REGISTRY: language -> versions -> config
# ================================================================

LANGUAGES = {
    "python": {
        "display": "Python",
        "versions": {
            ver: {"docker_image": img, "local_cmd": "python3"}
            for ver, img in settings.python_versions.items()
        },
        "default_version": settings.python_default_version,
        "extension": ".py",
        "run_cmd": ["python3", "{file}"],
        "install_cmd": ["pip", "install", "--quiet", "--target", "{deps_dir}"],
        "env_var": "PYTHONPATH",
        "output_type": "text",
        "example": 'print("Hello, World!")',
    },
    "javascript": {
        "display": "Node.js",
        "versions": {
            ver: {"docker_image": img, "local_cmd": "node"}
            for ver, img in settings.javascript_versions.items()
        },
        "default_version": settings.javascript_default_version,
        "extension": ".js",
        "run_cmd": ["node", "{file}"],
        "install_cmd": ["npm", "install", "--prefix", "{deps_dir}"],
        "env_var": "NODE_PATH",
        "output_type": "text",
        "example": 'console.log("Hello, World!");',
    },
    "go": {
        "display": "Go",
        "versions": {
            ver: {"docker_image": img, "local_cmd": "go"}
            for ver, img in settings.go_versions.items()
        },
        "default_version": settings.go_default_version,
        "extension": ".go",
        "run_cmd": ["go", "run", "{file}"],
        "install_cmd": ["go", "get"],
        "env_var": "GOPATH",
        "output_type": "text",
        "example": 'package main\n\nimport "fmt"\n\nfunc main() {\n\tfmt.Println("Hello, World!")\n}',
    },
    "bash": {
        "display": "Bash",
        "versions": {
            ver: {"docker_image": img, "local_cmd": "bash"}
            for ver, img in settings.bash_versions.items()
        },
        "default_version": settings.bash_default_version,
        "extension": ".sh",
        "run_cmd": ["bash", "{file}"],
        "install_cmd": None,
        "env_var": None,
        "output_type": "text",
        "example": 'echo "Hello, World!"',
    },
    "java": {
        "display": "Java",
        "versions": {
            ver: {"docker_image": img, "local_cmd": "java"}
            for ver, img in settings.java_versions.items()
        },
        "default_version": settings.java_default_version,
        "extension": ".java",
        "run_cmd": ["java", "{file}"],
        "install_cmd": None,
        "env_var": "CLASSPATH",
        "output_type": "text",
        "example": 'public class Main {\n    public static void main(String[] args) {\n        System.out.println("Hello, World!");\n    }\n}',
    },
    "csharp": {
        "display": "C#",
        "versions": {
            ver: {"docker_image": img, "local_cmd": "dotnet"}
            for ver, img in settings.csharp_versions.items()
        },
        "default_version": settings.csharp_default_version,
        "extension": ".cs",
        "run_cmd": ["dotnet", "run"],
        "install_cmd": ["dotnet", "add", "package"],
        "env_var": None,
        "output_type": "text",
        "example": 'using System;\n\nConsole.WriteLine("Hello, World!");',
    },
    "html": {
        "display": "HTML/CSS/JS",
        "versions": {
            ver: {"docker_image": img, "local_cmd": "__static__"}
            for ver, img in settings.html_versions.items()
        },
        "default_version": settings.html_default_version,
        "extension": ".html",
        "run_cmd": None,
        "install_cmd": None,
        "env_var": None,
        "output_type": "html",
        "example": '<!DOCTYPE html>\n<html>\n<head>\n  <style>\n    body { font-family: sans-serif; background: #1a1a2e; color: #eee; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }\n    .card { background: #16213e; padding: 2rem; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.3); text-align: center; }\n    h1 { background: linear-gradient(135deg, #e94560, #0f3460); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }\n  </style>\n</head>\n<body>\n  <div class="card">\n    <h1>Hello World!</h1>\n    <p id="time"></p>\n  </div>\n  <script>document.getElementById("time").textContent = new Date().toLocaleString();</script>\n</body>\n</html>',
    },
    "react": {
        "display": "React",
        "versions": {
            ver: {"docker_image": img, "local_cmd": "__static__"}
            for ver, img in settings.react_versions.items()
        },
        "default_version": settings.react_default_version,
        "extension": ".jsx",
        "run_cmd": None,
        "install_cmd": None,
        "env_var": None,
        "output_type": "html",
        "example": 'function App() {\n  const [count, setCount] = React.useState(0);\n  return (\n    <div style={{fontFamily: "sans-serif", background: "#1a1a2e", color: "#eee", display: "flex", justifyContent: "center", alignItems: "center", height: "100vh", margin: 0}}>\n      <div style={{background: "#16213e", padding: "2rem", borderRadius: "12px", boxShadow: "0 8px 32px rgba(0,0,0,0.3)", textAlign: "center"}}>\n        <h1 style={{background: "linear-gradient(135deg, #e94560, #0f3460)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent"}}>React Counter</h1>\n        <p style={{fontSize: "3rem", margin: "1rem 0"}}>{count}</p>\n        <button onClick={() => setCount(c => c + 1)} style={{padding: "0.5rem 2rem", fontSize: "1rem", borderRadius: "8px", border: "none", background: "#e94560", color: "white", cursor: "pointer"}}>Click me!</button>\n      </div>\n    </div>\n  );\n}',
    },
}

# Flat config for /languages endpoint
LANGUAGE_CONFIG = {}
for lang_name, lang_data in LANGUAGES.items():
    LANGUAGE_CONFIG[lang_name] = {
        "version": lang_data["default_version"],
        "versions": list(lang_data["versions"].keys()),
        "display": lang_data["display"],
        "extension": lang_data["extension"],
        "example": lang_data["example"],
        "output_type": lang_data.get("output_type", "text"),
    }


def _check_local_availability() -> dict[str, bool]:
    """Check which language runtimes are available locally."""
    available = {}
    for lang_name, lang_data in LANGUAGES.items():
        default_ver = lang_data["default_version"]
        cmd = lang_data["versions"][default_ver]["local_cmd"]
        available[lang_name] = shutil.which(cmd) is not None
    return available


class SandboxManager:
    """Executes code in Docker containers, or locally via subprocess as fallback."""

    def __init__(self):
        self._docker_client = None
        self._docker_available = False
        self._local_langs = _check_local_availability()
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_executions)

    def _init_docker(self):
        """Try to initialise Docker client."""
        try:
            import docker
            self._docker_client = docker.DockerClient(base_url=settings.docker_base_url)
            self._docker_client.ping()
            self._docker_available = True
            logger.info("✅ Docker daemon is reachable")
        except Exception:
            self._docker_available = False
            self._docker_client = None
            avail = [l for l, ok in self._local_langs.items() if ok]
            logger.warning(
                "⚠️  Docker unavailable — using local subprocess for: %s",
                ", ".join(avail) or "none",
            )

    def is_healthy(self) -> bool:
        return self._docker_available or any(self._local_langs.values())

    def ensure_sandbox_image(self) -> bool:
        if not self._docker_available:
            return False
        try:
            from docker.errors import ImageNotFound
            self._docker_client.images.get(settings.sandbox_image)
            return True
        except Exception:
            return False

    async def execute_code(
        self,
        execution_id: str,
        code: str,
        language: str,
        version: Optional[str] = None,
        stdin: Optional[str] = None,
        timeout: Optional[int] = None,
        memory_limit: Optional[str] = None,
        dependencies: Optional[list[str]] = None,
    ) -> dict:
        """Execute code — Docker if available, otherwise local subprocess."""
        # Resolve language and version
        lang_data = LANGUAGES.get(language)
        if not lang_data:
            return self._fail(f"Unsupported language: {language}")

        resolved_version = version or lang_data["default_version"]
        if resolved_version not in lang_data["versions"]:
            return self._fail(
                f"Unsupported version '{resolved_version}' for {language}. "
                f"Available: {list(lang_data['versions'].keys())}"
            )

        # -- WEB EXECUTION SHORT CIRCUIT --
        if language in ["html", "react"]:
            start_time = time.monotonic()
            html_content = code
            if language == "react":
                html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <script src="https://unpkg.com/react@18/umd/react.development.js" crossorigin></script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js" crossorigin></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
</head>
<body>
  <div id="root"></div>
  <script type="text/babel">
{code}
    if (typeof App !== 'undefined') {{
      const root = ReactDOM.createRoot(document.getElementById('root'));
      root.render(React.createElement(App));
    }}
  </script>
</body>
</html>"""
            elapsed_ms = (time.monotonic() - start_time) * 1000
            return {
                "status": ExecutionStatus.COMPLETED,
                "stdout": html_content,
                "stderr": "",
                "exit_code": 0,
                "execution_time_ms": round(elapsed_ms, 2)
            }

        async with self._semaphore:
            # Prefer local subprocess when the runtime is available locally
            # (faster, no image pull needed, avoids shell compatibility issues)
            if self._local_langs.get(language):
                return await asyncio.get_event_loop().run_in_executor(
                    None, self._execute_local, execution_id, code, language,
                    resolved_version, stdin, timeout or settings.default_timeout,
                    dependencies,
                )
            elif self._docker_available:
                ver_data = lang_data["versions"][resolved_version]
                docker_image = ver_data["docker_image"]
                try:
                    self._docker_client.images.get(docker_image)
                except Exception:
                    try:
                        logger.info("Pulling Docker image %s...", docker_image)
                        self._docker_client.images.pull(docker_image)
                    except Exception:
                        return self._fail(
                            f"'{lang_data['display']}' not found locally and "
                            f"Docker image '{docker_image}' could not be pulled."
                        )
                return await asyncio.get_event_loop().run_in_executor(
                    None, self._execute_docker, execution_id, code, language,
                    resolved_version, stdin, timeout or settings.default_timeout,
                    memory_limit or settings.default_memory_limit, dependencies,
                )
            else:
                return self._fail(
                    f"'{lang_data['display']}' not found locally and Docker is not available."
                )

    # ------------------------------------------------------------------ #
    #  LOCAL SUBPROCESS EXECUTION (dev fallback)                          #
    # ------------------------------------------------------------------ #

    def _install_deps_local(
        self, lang_data: dict, deps: list[str], deps_dir: str, timeout: int,
    ) -> Optional[str]:
        """Install dependencies locally. Returns error string or None on success."""
        install_template = lang_data.get("install_cmd")
        if not install_template:
            return f"Dependency installation not supported for {lang_data['display']}"

        cmd = [p.replace("{deps_dir}", deps_dir) for p in install_template] + deps
        logger.info("Installing dependencies: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout, cwd=deps_dir,
            )
            if result.returncode != 0:
                return f"Dependency install failed:\n{result.stderr}"
            return None
        except subprocess.TimeoutExpired:
            return "Dependency installation timed out"
        except Exception as e:
            return f"Dependency install error: {e}"

    def _execute_local(
        self, execution_id: str, code: str, language: str, version: str,
        stdin: Optional[str], timeout: int,
        dependencies: Optional[list[str]] = None,
    ) -> dict:
        """Execute code in a local subprocess."""
        lang_data = LANGUAGES[language]

        if not self._local_langs.get(language):
            return self._fail(
                f"'{lang_data['display']}' not found locally. "
                f"Install it or start Docker."
            )

        tmpdir = tempfile.mkdtemp(prefix=f"exec-{execution_id[:8]}-")
        deps_dir = os.path.join(tmpdir, "deps")
        os.makedirs(deps_dir, exist_ok=True)
        start_time = time.monotonic()

        try:
            # Install dependencies
            if dependencies:
                err = self._install_deps_local(lang_data, dependencies, deps_dir, timeout)
                if err:
                    return self._fail(err)

            # Special handling for Java (needs class in file named Main.java)
            if language == "java":
                filepath = os.path.join(tmpdir, "Main.java")
            else:
                filepath = os.path.join(tmpdir, f"main{lang_data['extension']}")

            with open(filepath, "w") as f:
                f.write(code)

            # Build command
            if language == "java":
                # Compile & run
                compile_result = subprocess.run(
                    ["javac", filepath], capture_output=True, text=True, timeout=timeout, cwd=tmpdir,
                )
                if compile_result.returncode != 0:
                    elapsed = (time.monotonic() - start_time) * 1000
                    return {
                        "status": ExecutionStatus.FAILED,
                        "stdout": "", "stderr": compile_result.stderr,
                        "exit_code": compile_result.returncode,
                        "execution_time_ms": round(elapsed, 2),
                    }
                cmd = ["java", "-cp", tmpdir, "Main"]
            elif language == "csharp":
                if not shutil.which("dotnet"):
                    return self._fail("C# requires the .NET SDK. Install it from https://dotnet.microsoft.com/download")
                # Create a mini console project
                proj_dir = os.path.join(tmpdir, "csproject")
                subprocess.run(
                    ["dotnet", "new", "console", "-o", proj_dir, "--force"],
                    capture_output=True, text=True, timeout=30, cwd=tmpdir,
                )
                # Overwrite Program.cs with user code
                with open(os.path.join(proj_dir, "Program.cs"), "w") as pf:
                    pf.write(code)
                cmd = ["dotnet", "run", "--project", proj_dir]
            else:
                cmd = [p.replace("{file}", filepath) for p in lang_data["run_cmd"]]

            # Environment
            env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            env_var = lang_data.get("env_var")
            if dependencies and env_var:
                if language == "python":
                    env[env_var] = deps_dir
                elif language == "javascript":
                    env[env_var] = os.path.join(deps_dir, "node_modules")

            result = subprocess.run(
                cmd, input=stdin, capture_output=True, text=True,
                timeout=timeout, cwd=tmpdir, env=env,
            )

            elapsed_ms = (time.monotonic() - start_time) * 1000
            max_out = 100_000
            stdout = (result.stdout or "")[:max_out]
            stderr = (result.stderr or "")[:max_out]

            return {
                "status": ExecutionStatus.COMPLETED if result.returncode == 0 else ExecutionStatus.FAILED,
                "stdout": stdout, "stderr": stderr,
                "exit_code": result.returncode,
                "execution_time_ms": round(elapsed_ms, 2),
            }

        except subprocess.TimeoutExpired:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            return {
                "status": ExecutionStatus.TIMEOUT,
                "stdout": "", "stderr": f"Execution timed out after {timeout}s",
                "exit_code": 124, "execution_time_ms": round(elapsed_ms, 2),
            }
        except Exception as e:
            return self._fail(str(e))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    # ------------------------------------------------------------------ #
    #  DOCKER EXECUTION (production)                                      #
    # ------------------------------------------------------------------ #

    def _execute_docker(
        self, execution_id: str, code: str, language: str, version: str,
        stdin: Optional[str], timeout: int, memory_limit: str,
        dependencies: Optional[list[str]] = None,
    ) -> dict:
        """Execute code in an isolated Docker container with the right version image."""
        lang_data = LANGUAGES[language]
        ver_config = lang_data["versions"][version]
        docker_image = ver_config["docker_image"]

        container_name = f"exec-{execution_id[:12]}"
        container = None
        start_time = time.monotonic()

        try:
            ext = lang_data["extension"]
            escaped_code = code.replace("'", "'\\''")

            # Dependency installation in Docker
            deps_install = ""
            env_setup = ""
            if dependencies:
                deps_list = " ".join(dependencies)
                if language == "python":
                    deps_install = f"pip install --quiet --target /tmp/deps {deps_list} && "
                    env_setup = "PYTHONPATH=/tmp/deps "
                elif language == "javascript":
                    deps_install = f"cd /tmp && npm install --silent {deps_list} && "
                    env_setup = "NODE_PATH=/tmp/node_modules "
                elif language == "go":
                    deps_install = f"cd /tmp/code && go mod init main && go get {deps_list} && "
                elif language == "java":
                    # Generate a POM to download dependencies to /tmp/code/lib
                    deps_xml = "".join([f"<dependency><groupId>{d.split(':')[0] if ':' in d else 'unknown'}</groupId><artifactId>{d.split(':')[1] if ':' in d else d}</artifactId><version>{d.split(':')[2] if d.count(':') > 1 else 'LATEST'}</version></dependency>" for d in dependencies])
                    pom = f"<project><modelVersion>4.0.0</modelVersion><groupId>x</groupId><artifactId>x</artifactId><version>1</version><dependencies>{deps_xml}</dependencies></project>"
                    deps_install = (
                        f"apk add --quiet maven && "
                        f"mkdir -p /tmp/code/lib && "
                        f"echo '{pom}' > /tmp/code/pom.xml && "
                        f"mvn -q -f /tmp/code/pom.xml dependency:copy-dependencies -DoutputDirectory=/tmp/code/lib && "
                    )
                    env_setup = "CLASSPATH='/tmp/code/lib/*:/tmp/code' "
                # C# handles its own deps installation below

            # Command execution string construction
            if language == "java":
                filename = "Main.java"
                cp = "'-cp' '/tmp/code/lib/*:/tmp/code'" if dependencies else ""
                cmd_parts = f"javac {cp} /tmp/code/Main.java && java {cp} Main"
            elif language == "csharp":
                filename = "Program.cs"
                deps_str = " ".join([f"dotnet add package {d} >/dev/null && " for d in dependencies]) if dependencies else ""
                cmd_parts = (
                    "export DOTNET_CLI_HOME=/tmp DOTNET_NOLOGO=1 HOME=/tmp && "
                    "dotnet new console -o /tmp/proj --force --verbosity quiet 2>/dev/null && "
                    "cd /tmp/proj && "
                    f"{deps_str}"
                    "cp /tmp/code/Program.cs /tmp/proj/Program.cs && "
                    "dotnet run"
                )
            else:
                filename = f"main{ext}"
                cmd_parts = " ".join(
                    p.replace("{file}", f"/tmp/code/{filename}") for p in lang_data["run_cmd"]
                )

            if stdin:
                escaped_stdin = stdin.replace("'", "'\\''")
                shell_cmd = (
                    f"mkdir -p /tmp/code && {deps_install}"
                    f"echo '{escaped_code}' > /tmp/code/{filename} && "
                    f"echo '{escaped_stdin}' | {env_setup}{cmd_parts}"
                )
            else:
                shell_cmd = (
                    f"mkdir -p /tmp/code && {deps_install}"
                    f"echo '{escaped_code}' > /tmp/code/{filename} && "
                    f"{env_setup}{cmd_parts}"
                )

            # Container environment variables
            container_env = {}
            if language == "csharp":
                container_env.update({
                    "DOTNET_CLI_HOME": "/tmp",
                    "DOTNET_NOLOGO": "1",
                    "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
                    "HOME": "/tmp",
                })
            if language == "go":
                container_env["GOPATH"] = "/tmp/go"

            # Use version-specific Docker image instead of single sandbox image
            container = self._docker_client.containers.run(
                image=docker_image,
                command=["sh", "-c", shell_cmd],
                name=container_name,
                detach=True,
                network_mode="none" if language != "csharp" else None,
                read_only=True,
                mem_limit=memory_limit,
                nano_cpus=int(settings.default_cpu_limit * 1e9),
                cap_drop=["ALL"],
                security_opt=["no-new-privileges"],
                user="1000:1000",
                tmpfs={"/tmp": "size=256M,exec"},
                pids_limit=256,
                environment=container_env,
                labels={"code-executor": "true", "execution-id": execution_id},
            )

            result = container.wait(timeout=timeout)
            exit_code = result.get("StatusCode", -1)
            elapsed_ms = (time.monotonic() - start_time) * 1000

            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")

            max_out = 100_000
            return {
                "status": ExecutionStatus.COMPLETED if exit_code == 0 else ExecutionStatus.FAILED,
                "stdout": stdout[:max_out], "stderr": stderr[:max_out],
                "exit_code": exit_code, "execution_time_ms": round(elapsed_ms, 2),
            }

        except Exception as e:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            msg = str(e)
            is_timeout = "timed out" in msg.lower() or "read timeout" in msg.lower()
            return {
                "status": ExecutionStatus.TIMEOUT if is_timeout else ExecutionStatus.FAILED,
                "stdout": "", "stderr": f"{'Timeout' if is_timeout else 'Error'}: {msg}",
                "exit_code": 124 if is_timeout else 1,
                "execution_time_ms": round(elapsed_ms, 2),
            }
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass

    # ------------------------------------------------------------------ #

    @staticmethod
    def _fail(message: str) -> dict:
        return {
            "status": ExecutionStatus.FAILED, "stdout": "", "stderr": message,
            "exit_code": 1, "execution_time_ms": 0,
        }

    def cleanup(self):
        if self._docker_available and self._docker_client:
            try:
                for c in self._docker_client.containers.list(
                    all=True, filters={"label": "code-executor=true"}
                ):
                    try:
                        c.remove(force=True)
                    except Exception:
                        pass
            except Exception:
                pass

    def close(self):
        if self._docker_client:
            self._docker_client.close()
            self._docker_client = None


# Singleton
sandbox_manager = SandboxManager()
