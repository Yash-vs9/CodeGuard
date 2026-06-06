from pathlib import Path
from langchain.tools import tool
import subprocess

@tool
def list_files(root_path: str) -> str:
    """
    Recursively list all files and directories inside a project.
    Useful for understanding project structure.
    """

    root = Path(root_path)

    if not root.exists():
        return "Path does not exist."

    results = []

    for item in root.rglob("*"):
        results.append(str(item))

    return "\n".join(results[:5000])


BLOCKED_COMMANDS = [
    "rm",
    "rmdir",
    "mv",
    "cp",
    "chmod",
    "chown",
    "sudo",
    "dd",
    "mkfs",
    "shutdown",
    "reboot",
    "kill",
    "killall",
    "truncate",
    ">",
    ">>",
]

@tool
def run_terminal(command: str) -> str:
    """
    Execute safe read-only shell commands.
    """

    cmd_lower = command.lower()

    for blocked in BLOCKED_COMMANDS:
        if blocked in cmd_lower:
            return f"Blocked command detected: {blocked}"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )

        return (
            f"STDOUT:\n{result.stdout}\n\n"
            f"STDERR:\n{result.stderr}"
        )

    except Exception as e:
        return str(e)