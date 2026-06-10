from pathlib import Path
import subprocess
import difflib
import os
from langchain.tools import tool
from typing import List

# ── ANSI colors ───────────────────────────────────────────────────────────────
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    DIM     = "\033[2m"

# ── Commands that should never be run by the agent ────────────────────────────
BLOCKED_COMMANDS = [
    "npm run dev", "npm start", "npm run start",
    "yarn dev", "yarn start",
    "pnpm dev", "pnpm start",
    "python manage.py runserver",
    "python -m flask run", "flask run",
    "uvicorn", "gunicorn",
    "next dev", "next start",
    "vite", "vite dev",
    "ng serve",
    "rails server", "rails s",
]

def _abs(path: str) -> Path:
    """
    Resolve path to absolute.
    - If already absolute → use as-is.
    - If relative → resolve against AGENT_WORKING_DIR env var.
    - Fallback → cwd.
    """
    p = Path(path)
    if p.is_absolute():
        return p.resolve()
    base = Path(os.environ.get("AGENT_WORKING_DIR", "."))
    return (base / p).resolve()

def _is_blocked(command: str) -> bool:
    cmd = command.strip().lower()
    return any(blocked in cmd for blocked in BLOCKED_COMMANDS)

def _banner(action: str, color: str, path: str = None):
    label = f"{color}{C.BOLD}[{action}]{C.RESET}"
    loc   = f"{C.DIM}{path}{C.RESET}" if path else ""
    print(f"\n{label} {loc}")

def _divider(color: str = C.DIM):
    print(f"{color}{'─' * 52}{C.RESET}")

def _approve(action: str, path: str) -> bool:
    """Ask user to confirm a destructive operation. Returns True if approved."""
    _divider(C.YELLOW)
    print(f"{C.YELLOW}{C.BOLD}⚠  Approval needed{C.RESET}")
    print(f"   Action : {C.CYAN}{action}{C.RESET}")
    print(f"   Target : {C.WHITE}{path}{C.RESET}")
    _divider(C.YELLOW)
    answer = input(f"{C.YELLOW}Proceed? [y/N]: {C.RESET}").strip().lower()
    approved = answer in ("y", "yes")
    if approved:
        print(f"{C.GREEN}✔  Approved{C.RESET}")
    else:
        print(f"{C.RED}✘  Cancelled by user{C.RESET}")
    return approved


# ── File Operations ────────────────────────────────────────────────────────────

@tool
def read_file(path: str) -> str:
    """Read and return the contents of a file."""
    abs_path = _abs(path)
    _banner("READ FILE", C.BLUE, abs_path)
    try:
        content = abs_path.read_text(encoding="utf-8")
        size = len(content.splitlines())
        print(f"{C.DIM}   {size} lines read{C.RESET}")
        return content
    except Exception as e:
        print(f"{C.RED}✘  Error: {e}{C.RESET}")
        return f"ERROR reading {abs_path}: {e}"


@tool
def create_file(path: str, content: str) -> str:
    """Create a new file with the given content."""
    abs_path = _abs(path)
    _banner("CREATE FILE", C.GREEN, abs_path)
    try:
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(content, encoding="utf-8")
        print(f"{C.GREEN}✔  Created:{C.RESET} {abs_path}")
        return f"Created {abs_path}"
    except Exception as e:
        print(f"{C.RED}✘  Error: {e}{C.RESET}")
        return f"ERROR creating {abs_path}: {e}"


@tool
def overwrite_file(path: str, content: str) -> str:
    """
    Completely overwrite an existing file with new content.
    Prefer this over edit_file when replacing most of the file content,
    or when you are unsure if the exact old text will match.
    """
    abs_path = _abs(path)
    _banner("OVERWRITE FILE", C.MAGENTA, abs_path)
    try:
        abs_path.write_text(content, encoding="utf-8")
        print(f"{C.MAGENTA}✔  Overwritten:{C.RESET} {abs_path}")
        return f"Updated {abs_path}"
    except Exception as e:
        print(f"{C.RED}✘  Error: {e}{C.RESET}")
        return f"ERROR overwriting {abs_path}: {e}"


@tool
def edit_file(path: str, old: str, new: str) -> str:
    """
    Replace the first occurrence of 'old' with 'new' in a file.
    Use this only for small, targeted edits where you are certain
    the exact text of 'old' exists in the file.
    If unsure, use read_file first to confirm the exact text, then edit.
    If the target text is not found, returns an error string — it does NOT crash.
    """
    abs_path = _abs(path)
    _banner("EDIT FILE", C.CYAN, abs_path)

    try:
        content = abs_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"{C.RED}✘  Could not read file: {e}{C.RESET}")
        return f"ERROR reading {abs_path}: {e}"

    if old not in content:
        # Show a helpful hint: find closest matching lines
        old_first_line = old.strip().splitlines()[0].strip() if old.strip() else ""
        hint_lines = [
            line for line in content.splitlines()
            if old_first_line[:20] in line
        ]
        hint = f" Closest match in file: {hint_lines[0]!r}" if hint_lines else ""
        msg = (
            f"ERROR: Target text not found in {abs_path}.{hint} "
            f"Use read_file to confirm the exact text before editing."
        )
        print(f"{C.RED}✘  {msg}{C.RESET}")
        return msg

    # Show a mini diff preview
    diff = list(difflib.unified_diff(
        old.splitlines(), new.splitlines(),
        fromfile="before", tofile="after", lineterm=""
    ))
    if diff:
        print(f"{C.DIM}   Preview:{C.RESET}")
        for line in diff[:12]:
            if line.startswith("+"):
                print(f"   {C.GREEN}{line}{C.RESET}")
            elif line.startswith("-"):
                print(f"   {C.RED}{line}{C.RESET}")
            else:
                print(f"   {C.DIM}{line}{C.RESET}")
        if len(diff) > 12:
            print(f"   {C.DIM}... ({len(diff) - 12} more lines){C.RESET}")

    try:
        content = content.replace(old, new, 1)
        abs_path.write_text(content, encoding="utf-8")
        print(f"{C.CYAN}✔  Edited:{C.RESET} {abs_path}")
        return f"Edited {abs_path}"
    except Exception as e:
        print(f"{C.RED}✘  Error: {e}{C.RESET}")
        return f"ERROR writing {abs_path}: {e}"


@tool
def delete_file(path: str) -> str:
    """Delete a file."""
    abs_path = _abs(path)
    _banner("DELETE FILE", C.RED, abs_path)
    if not _approve("Delete file", abs_path):
        return f"Cancelled — {abs_path} was not deleted."
    try:
        abs_path.unlink(missing_ok=True)
        print(f"{C.RED}✔  Deleted:{C.RESET} {abs_path}")
        return f"Deleted {abs_path}"
    except Exception as e:
        print(f"{C.RED}✘  Error: {e}{C.RESET}")
        return f"ERROR deleting {abs_path}: {e}"


# ── Directory Operations ───────────────────────────────────────────────────────

@tool
def list_dir(path: str = ".") -> List[str]:
    """List files and directories."""
    abs_path = _abs(path)
    _banner("LIST DIR", C.BLUE, abs_path)
    try:
        entries = sorted([str(p) for p in abs_path.iterdir()])
        for e in entries:
            icon = "📁" if Path(e).is_dir() else "📄"
            print(f"   {icon}  {C.DIM}{e}{C.RESET}")
        return entries
    except Exception as e:
        print(f"{C.RED}✘  Error: {e}{C.RESET}")
        return [f"ERROR listing {abs_path}: {e}"]


@tool
def find_files(pattern: str, root: str = ".") -> List[str]:
    """
    Find files matching a glob pattern.

    Example:
        find_files("*.py")
        find_files("**/*.java")
    """
    abs_root = _abs(root)
    _banner("FIND FILES", C.BLUE, abs_root)
    print(f"   {C.DIM}Pattern: {pattern}{C.RESET}")
    try:
        results = [str(p) for p in abs_root.glob(pattern)]
        print(f"   {C.GREEN}{len(results)} match(es) found{C.RESET}")
        for r in results:
            print(f"   {C.DIM}→ {r}{C.RESET}")
        return results
    except Exception as e:
        print(f"{C.RED}✘  Error: {e}{C.RESET}")
        return [f"ERROR finding files in {abs_root}: {e}"]


# ── Search ─────────────────────────────────────────────────────────────────────

@tool
def search_in_files(query: str, root: str = ".") -> List[str]:
    """
    Search for text inside files.
    Returns matching file paths.
    """
    abs_root = _abs(root)
    _banner("SEARCH IN FILES", C.CYAN, abs_root)
    print(f"   {C.DIM}Query: \"{query}\"{C.RESET}")
    matches = []
    for file in abs_root.rglob("*"):
        if file.is_file():
            try:
                text = file.read_text(encoding="utf-8", errors="ignore")
                if query in text:
                    matches.append(str(file))
                    print(f"   {C.GREEN}✔  {file}{C.RESET}")
            except Exception:
                pass
    if not matches:
        print(f"   {C.YELLOW}No matches found{C.RESET}")
    return matches


# ── Terminal ───────────────────────────────────────────────────────────────────

@tool
def run_command(command: str, cwd: str = ".") -> str:
    """
    Execute a shell command.
    Do NOT use for long-running servers or dev commands
    (e.g. npm run dev, flask run, uvicorn). Those will hang forever.
    Only use for commands that terminate on their own (install, build, test, ls, mkdir etc.)
    """
    abs_cwd = _abs(cwd)
    _banner("RUN COMMAND", C.MAGENTA, abs_cwd)

    if _is_blocked(command):
        msg = (
            f"BLOCKED: '{command}' is a long-running dev server command and cannot "
            f"be run by the agent. Tell the user to run it manually: "
            f"`cd {abs_cwd} && {command}`"
        )
        print(f"{C.RED}✘  {msg}{C.RESET}")
        return msg

    print(f"   {C.BOLD}$ {command}{C.RESET}")
    _divider(C.DIM)

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=abs_cwd,
            capture_output=True,
            text=True,
            input="y\n",
            timeout=60,
        )
        if result.stdout.strip():
            print(f"{C.DIM}{result.stdout.strip()}{C.RESET}")
        if result.stderr.strip():
            print(f"{C.RED}{result.stderr.strip()}{C.RESET}")
        color = C.GREEN if result.returncode == 0 else C.RED
        print(f"{color}   Exit code: {result.returncode}{C.RESET}")
        return (
            f"Exit Code: {result.returncode}\n\n"
            f"STDOUT:\n{result.stdout}\n\n"
            f"STDERR:\n{result.stderr}"
        )
    except subprocess.TimeoutExpired:
        msg = (
            f"TimeoutExpired: Command killed after 60s. "
            f"If this was a dev server, tell the user to run it manually: "
            f"`cd {abs_cwd} && {command}`"
        )
        print(f"{C.YELLOW}   ⚠  {msg}{C.RESET}")
        return msg
    except Exception as e:
        print(f"{C.RED}✘  Error: {e}{C.RESET}")
        return f"ERROR running command '{command}': {e}"


# ── Git ────────────────────────────────────────────────────────────────────────

@tool
def git_diff(cwd: str = ".") -> str:
    """Return current git diff."""
    return run_command.invoke({"command": "git diff", "cwd": cwd})


# ── Testing ────────────────────────────────────────────────────────────────────

@tool
def run_tests(command: str = "pytest", cwd: str = ".") -> str:
    """Run project tests."""
    return run_command.invoke({"command": command, "cwd": cwd})


# ── Diff Preview ───────────────────────────────────────────────────────────────

@tool
def preview_changes(old: str, new: str) -> str:
    """Generate a unified diff without modifying files."""
    _banner("PREVIEW CHANGES", C.YELLOW)
    diff = list(difflib.unified_diff(
        old.splitlines(), new.splitlines(),
        fromfile="before", tofile="after", lineterm=""
    ))
    for line in diff:
        if line.startswith("+"):
            print(f"{C.GREEN}{line}{C.RESET}")
        elif line.startswith("-"):
            print(f"{C.RED}{line}{C.RESET}")
        else:
            print(f"{C.DIM}{line}{C.RESET}")
    return "\n".join(diff)


# ── Web Search ─────────────────────────────────────────────────────────────────

from serpapi import GoogleSearch

@tool
def search_web(query: str, num_results: int = 5) -> str:
    """
    Search Google using SerpAPI and return formatted results.

    Requires:
        export SERPAPI_API_KEY="your_api_key"
    """
    _banner("WEB SEARCH", C.CYAN)
    print(f"   {C.DIM}Query: \"{query}\"{C.RESET}")
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return "ERROR: SERPAPI_API_KEY environment variable not found."

    try:
        search = GoogleSearch({
            "q": query,
            "api_key": api_key,
            "engine": "google",
            "num": num_results,
        })
        results = search.get_dict()
        organic_results = results.get("organic_results", [])

        if not organic_results:
            print(f"   {C.YELLOW}No results found{C.RESET}")
            return "No search results found."

        output = []
        for i, result in enumerate(organic_results, 1):
            title   = result.get("title", "")
            link    = result.get("link", "")
            snippet = result.get("snippet", "")
            print(f"   {C.BOLD}{i}. {title}{C.RESET}")
            print(f"   {C.DIM}{link}{C.RESET}")
            output.append(f"{i}. {title}\nURL: {link}\nSnippet: {snippet}\n")

        return "\n".join(output)
    except Exception as e:
        print(f"{C.RED}✘  Error: {e}{C.RESET}")
        return f"ERROR during web search: {e}"


# ── Ask User ───────────────────────────────────────────────────────────────────

@tool
def ask_user(question: str) -> str:
    """Ask the user for clarification and wait for a response."""
    _divider(C.CYAN)
    print(f"{C.CYAN}{C.BOLD}🤖  Agent needs your input{C.RESET}")
    _divider(C.CYAN)
    print(f"{C.WHITE}{question}{C.RESET}")
    _divider(C.DIM)
    response = input(f"{C.CYAN}Your response: {C.RESET}").strip()
    while not response:
        response = input(f"{C.YELLOW}Please enter a response: {C.RESET}").strip()
    return response