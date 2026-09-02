import subprocess
import sys


def run_code(code: str, timeout: int = 10) -> dict:
    """Execute Python code in a subprocess and capture the result.

    Args:
        code: The Python source code to execute
        timeout: Max seconds before the process is killed

    Returns:
        dict with keys: exit_code, stdout, stderr, timed_out
    """
    try:
        result = subprocess.run(
            [sys.executable, "-I", "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        return {
            "exit_code": None,
            "stdout": "",
            "stderr": f"Timed out after {timeout} seconds",
            "timed_out": True,
        }