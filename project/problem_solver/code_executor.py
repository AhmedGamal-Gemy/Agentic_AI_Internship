import subprocess
import sys
import tempfile
from pathlib import Path

from google.adk.code_executors.base_code_executor import (
    BaseCodeExecutor,
    CodeExecutionInput,
    CodeExecutionResult,
)


class LocalSubprocessCodeExecutor(BaseCodeExecutor):
    """Runs model code blocks in a local subprocess with a timeout.

    Fallback executor used when the Docker daemon is unavailable. Executes
    in a temp directory and is bounded by ``timeout_seconds``.
    """

    def execute_code(
        self,
        invocation_context,
        code_execution_input: CodeExecutionInput,
    ) -> CodeExecutionResult:
        timeout = self.timeout_seconds or 60
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "script.py"
            script.write_text(code_execution_input.code, encoding="utf-8")
            try:
                proc = subprocess.run(
                    [sys.executable, str(script)],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=tmp,
                )
                return CodeExecutionResult(stdout=proc.stdout, stderr=proc.stderr)
            except subprocess.TimeoutExpired:
                return CodeExecutionResult(
                    stdout="", stderr=f"Execution timed out after {timeout}s"
                )
            except Exception as e:  # noqa: BLE001
                return CodeExecutionResult(stdout="", stderr=str(e))


def get_code_executor() -> BaseCodeExecutor:
    """Return the best available code executor.

    Prefers the sandboxed container executor (Docker); falls back to a
    local subprocess executor when Docker is not running.
    """
    try:
        from google.adk.code_executors.container_code_executor import (
            ContainerCodeExecutor,
        )

        return ContainerCodeExecutor(
            image="adk-code-executor:latest", timeout_seconds=60
        )
    except Exception:  # noqa: BLE001 - Docker daemon not available
        return LocalSubprocessCodeExecutor(timeout_seconds=60)