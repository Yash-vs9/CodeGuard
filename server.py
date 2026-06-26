"""
CodeGuard MCP Server
Wraps the existing CodeGuard CLI (main.py, -m scan mode) as an MCP tool.

IMPORTANT: -m scan REQUIRES -q (query). Without it, the CLI drops into an
interactive Prompt.ask() chat loop waiting on stdin, which will hang forever
when invoked as a subprocess (no TTY). So this tool always passes -q.

Output is captured via plain redirection: Rich's console writes ANSI styling
even when piped, so we strip ANSI codes from stdout before returning it to
the MCP client.

Run directly to sanity-check:
    python3 server.py
Run via MCP CLI dev inspector:
    mcp dev server.py
"""

import os
import re
import subprocess
from mcp.server.fastmcp import FastMCP

# ---- CONFIG: point this at your actual CodeGuard CLI entrypoint ----
# Use the venv's real interpreter, not bare "python3" — subprocess won't
# inherit an activated venv, so langchain etc. won't be found otherwise.

PYTHON_BIN = "/Users/yash/Desktop/code_agent/.venv/bin/python3"   # <-- confirm this matches `which python3` after activating .venv
MAIN_PY_PATH = "/Users/yash/Desktop/code_agent/cli.py"           # <-- set this
PROJECT_CWD = os.path.dirname(MAIN_PY_PATH)  # run main.py from its own dir, regardless of Claude Desktop's CWD
TIMEOUT_SECONDS = 3600  # scan mode runs 3 agents sequentially, give it room

mcp = FastMCP(
    "codeguard",
    host="0.0.0.0",
    port=8000,
)
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


@mcp.tool()
def analyze_codebase(path: str, query: str = "Scan this project for security, logic, and quality issues.") -> str:
    """
    Run a full CodeGuard scan (security, logic, quality agents) on the
    given project path and return the combined report.

    Args:
        path: Absolute path to the project directory to analyze.
        query: What to focus the scan on. Defaults to a general full scan.
               Always provide this explicitly — without it the underlying
               CLI would otherwise wait for interactive input.
    """
    cmd = [
        PYTHON_BIN, MAIN_PY_PATH,
        "-m", "scan",
        "-p", path,
        "-q", query,
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_CWD,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return (
            f"CodeGuard timed out after {TIMEOUT_SECONDS}s analyzing {path}. "
            "Scan mode runs security + logic + quality agents sequentially; "
            "consider raising TIMEOUT_SECONDS for larger repos."
        )
    except FileNotFoundError:
        return (
            "Could not find main.py. Check MAIN_PY_PATH in server.py "
            "points to the correct absolute path."
        )

    stdout = _strip_ansi(result.stdout)

    if result.returncode != 0:
        stderr = _strip_ansi(result.stderr)
        return f"CodeGuard exited with error (code {result.returncode}):\n{stderr}\n\n--- partial stdout ---\n{stdout}"

    return stdout or "CodeGuard ran successfully but produced no captured output."


@mcp.tool()
def write_code(path: str, query: str) -> str:
    """
    Write code either to build a new project or to fix existing codebase

    Args:
        path: Absolute path to the project directory to write code on.
        query: What project to build, or what issues to fix.
    """
    cmd = [
        PYTHON_BIN, MAIN_PY_PATH,
        "-m", "code",
        "-p", path,
        "-q", query,
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_CWD,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return (
            f"CodeGuard timed out after {TIMEOUT_SECONDS}s analyzing {path}. "
            "consider raising TIMEOUT_SECONDS for larger repos."
        )
    except FileNotFoundError:
        return (
            "Could not find main.py. Check MAIN_PY_PATH in server.py "
            "points to the correct absolute path."
        )

    stdout = _strip_ansi(result.stdout)

    if result.returncode != 0:
        stderr = _strip_ansi(result.stderr)
        return f"CodeGuard exited with error (code {result.returncode}):\n{stderr}\n\n--- partial stdout ---\n{stdout}"

    return stdout or "CodeGuard ran successfully but produced no captured output."


if __name__ == "__main__":
        mcp.run(transport="streamable-http")


