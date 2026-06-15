import os
import time
import subprocess
import difflib
from pathlib import Path
from typing import List
from langchain.tools import tool

# ── Global Caches and Constants ───────────────────────────────────────────────

IGNORE_DIRS = {
    ".git", ".next", "node_modules", "dist", "build", "out",
    "coverage", ".turbo", ".cache", "__pycache__", ".venv", "venv"
}

BINARY_EXTENSIONS = {
    ".pyc", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf",
    ".mp4", ".mp3", ".wav", ".avi", ".mov", ".exe", ".dll", ".so", ".dylib",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar", ".iso", ".bin", ".wasm"
}

MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB

FILE_CACHE = {}
DIR_CACHE = {}

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
    "grep -r", "find .", "find -exec", "ls -r", "tree"
]

BLOCKED_PATHS_IN_CMD = [
    ".next", "node_modules", "dist", "build", "coverage", ".git"
]

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

# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_agent_dir() -> Path:
    return Path(os.environ.get("AGENT_WORKING_DIR", ".")).resolve()

def _validate_path(path: str) -> Path:
    """
    Resolve and validate path.
    Rejects paths in IGNORE_DIRS, outside AGENT_WORKING_DIR, or traversal attempts.
    """
    base = _get_agent_dir()
    p = Path(path)
    
    if p.is_absolute():
        resolved = p.resolve()
    else:
        resolved = (base / p).resolve()
        
    try:
        resolved.relative_to(base)
    except ValueError:
        raise ValueError(f"Path '{resolved}' escapes agent working directory '{base}'.")

    rel_parts = resolved.relative_to(base).parts
    for part in rel_parts:
        if part in IGNORE_DIRS:
            raise ValueError(f"Path accesses ignored directory: '{part}'")
            
    return resolved

def _is_binary(path: Path) -> bool:
    return path.suffix.lower() in BINARY_EXTENSIONS

def _invalidate_file_cache(path: Path):
    FILE_CACHE.pop(str(path), None)
    DIR_CACHE.clear()

def _is_blocked(command: str) -> bool:
    cmd = command.strip().lower()
    
    for blocked in BLOCKED_COMMANDS:
        if blocked in cmd:
            return True
            
    if "rg " in cmd and "--glob" not in cmd and "-g" not in cmd and "--ignore" not in cmd:
        return True
        
    if "cat " in cmd:
        return True

    for blocked in BLOCKED_PATHS_IN_CMD:
        if f" {blocked}" in cmd or f"/{blocked}" in cmd or f"'{blocked}'" in cmd or f'"{blocked}"' in cmd:
            return True
            
    return False

def _banner(action: str, color: str, path: str = None, elapsed: float = None):
    label = f"{color}{C.BOLD}[{action}]{C.RESET}"
    loc   = f"{C.DIM}{path}{C.RESET}" if path else ""
    time_str = f" {C.DIM}({elapsed:.2f}s){C.RESET}" if elapsed is not None else ""
    print(f"\n{label} {loc}{time_str}")

def _divider(color: str = C.DIM):
    print(f"{color}{'─' * 52}{C.RESET}")

def _approve(action: str, path: str, reason: str = "") -> bool:
    """Ask user to confirm a destructive operation. Returns True if approved."""
    _divider(C.YELLOW)
    print(f"{C.YELLOW}{C.BOLD}⚠ Approval Required{C.RESET}\n")
    print(f"{C.BOLD}Action:{C.RESET} {C.CYAN}{action}{C.RESET}")
    print(f"{C.BOLD}Target:{C.RESET} {C.WHITE}{path}{C.RESET}")
    if reason:
        print(f"{C.BOLD}Reason:{C.RESET} {reason}")
    print("")
    print(f"{C.GREEN}[y] Yes{C.RESET}")
    print(f"{C.RED}[n] No{C.RESET}")
    _divider(C.YELLOW)
    answer = input(f"{C.YELLOW}Proceed? [y/n]: {C.RESET}").strip().lower()
    approved = answer == "y"
    if approved:
        print(f"{C.GREEN}✔ Approved{C.RESET}")
    else:
        print(f"{C.RED}✘ Cancelled by user{C.RESET}")
    return approved

# ── File Operations ────────────────────────────────────────────────────────────

@tool
def read_file(path: str) -> str:
    """Read and return the contents of a file."""
    start_time = time.time()
    try:
        abs_path = _validate_path(path)
        _banner("READ", C.BLUE, abs_path)
        
        if _is_binary(abs_path):
            msg = f"ERROR: '{abs_path}' is a binary file. Reading binary files is not allowed."
            print(f"{C.RED}✘ {msg}{C.RESET}")
            return msg

        if not abs_path.is_file():
            msg = f"ERROR: File '{abs_path}' does not exist."
            print(f"{C.RED}✘ {msg}{C.RESET}")
            return msg
            
        file_size = abs_path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            msg = f"ERROR: File '{abs_path}' exceeds 2MB limit. Use search_in_files or read partial lines if supported."
            print(f"{C.RED}✘ {msg}{C.RESET}")
            return msg

        mtime = abs_path.stat().st_mtime
        cache_key = str(abs_path)
        if cache_key in FILE_CACHE and FILE_CACHE[cache_key]['mtime'] == mtime:
            print(f"{C.DIM}   (Cache hit){C.RESET}")
            content = FILE_CACHE[cache_key]['content']
        else:
            content = abs_path.read_text(encoding="utf-8", errors="replace")
            FILE_CACHE[cache_key] = {'mtime': mtime, 'content': content}
            
        lines = content.splitlines()
        truncated = False
        if len(lines) > 500:
            lines = lines[:500]
            lines.append("\n... truncated ...")
            truncated = True
            
        result_content = "\n".join(lines)
        size = len(lines) - (1 if truncated else 0)
        print(f"{C.DIM}   {size} lines read{C.RESET}")
        
        elapsed = time.time() - start_time
        print(f"{C.GREEN}✔ Done ({elapsed:.2f}s){C.RESET}")
        return result_content
    except Exception as e:
        print(f"{C.RED}✘ Error: {e}{C.RESET}")
        return f"ERROR reading {path}: {e}"

@tool
def create_file(path: str, content: str) -> str:
    """Create a new file with the given content."""
    start_time = time.time()
    try:
        abs_path = _validate_path(path)
        _banner("WRITE", C.GREEN, abs_path)
        
        if abs_path.exists():
            return f"ERROR: File '{abs_path}' already exists. Use overwrite_file or edit_file instead."
            
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(content, encoding="utf-8")
        _invalidate_file_cache(abs_path)
        
        elapsed = time.time() - start_time
        print(f"{C.GREEN}✔ Created ({elapsed:.2f}s){C.RESET}")
        return f"Created {abs_path}"
    except Exception as e:
        print(f"{C.RED}✘ Error: {e}{C.RESET}")
        return f"ERROR creating {path}: {e}"

@tool
def overwrite_file(path: str, content: str) -> str:
    """Completely overwrite an existing file with new content."""
    start_time = time.time()
    try:
        abs_path = _validate_path(path)
        _banner("WRITE", C.MAGENTA, abs_path)
        
        if not _approve("Overwrite file", str(abs_path), "Completely replacing file contents."):
            return f"Cancelled — {abs_path} was not overwritten."
            
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(content, encoding="utf-8")
        _invalidate_file_cache(abs_path)
        
        elapsed = time.time() - start_time
        print(f"{C.MAGENTA}✔ Overwritten ({elapsed:.2f}s){C.RESET}")
        return f"Updated {abs_path}"
    except Exception as e:
        print(f"{C.RED}✘ Error: {e}{C.RESET}")
        return f"ERROR overwriting {path}: {e}"

@tool
def edit_file(path: str, old: str, new: str) -> str:
    """Replace the first occurrence of 'old' with 'new' in a file."""
    start_time = time.time()
    try:
        abs_path = _validate_path(path)
        _banner("EDIT", C.CYAN, abs_path)

        if not abs_path.is_file():
            msg = f"ERROR: File '{abs_path}' does not exist."
            print(f"{C.RED}✘ {msg}{C.RESET}")
            return msg

        content = abs_path.read_text(encoding="utf-8", errors="replace")

        if old not in content:
            old_first_line = old.strip().splitlines()[0].strip() if old.strip() else ""
            hint_lines = [
                line for line in content.splitlines()
                if old_first_line[:20] in line
            ]
            hint = f" Closest match in file: {hint_lines[0]!r}" if hint_lines else ""
            msg = f"ERROR: Target text not found in {abs_path}.{hint}"
            print(f"{C.RED}✘ {msg}{C.RESET}")
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

        content = content.replace(old, new, 1)
        abs_path.write_text(content, encoding="utf-8")
        _invalidate_file_cache(abs_path)
        
        elapsed = time.time() - start_time
        print(f"{C.CYAN}✔ Edited ({elapsed:.2f}s){C.RESET}")
        return f"Edited {abs_path}"
    except Exception as e:
        print(f"{C.RED}✘ Error: {e}{C.RESET}")
        return f"ERROR editing {path}: {e}"

@tool
def delete_file(path: str) -> str:
    """Delete a file."""
    start_time = time.time()
    try:
        abs_path = _validate_path(path)
        _banner("DELETE", C.RED, abs_path)
        
        # Prevent deleting the project root
        if abs_path == _get_agent_dir():
            msg = "ERROR: Cannot delete the project root."
            print(f"{C.RED}✘ {msg}{C.RESET}")
            return msg
            
        if not abs_path.exists():
            return f"ERROR: {abs_path} does not exist."
            
        if not _approve("Delete file", str(abs_path), "Removing file from disk."):
            return f"Cancelled — {abs_path} was not deleted."
            
        abs_path.unlink(missing_ok=True)
        _invalidate_file_cache(abs_path)
        
        elapsed = time.time() - start_time
        print(f"{C.RED}✔ Deleted ({elapsed:.2f}s){C.RESET}")
        return f"Deleted {abs_path}"
    except Exception as e:
        print(f"{C.RED}✘ Error: {e}{C.RESET}")
        return f"ERROR deleting {path}: {e}"

# ── Directory Operations ───────────────────────────────────────────────────────

@tool
def list_dir(path: str = ".") -> List[str]:
    """List files and directories."""
    start_time = time.time()
    try:
        abs_path = _validate_path(path)
        _banner("READ", C.BLUE, abs_path)
        
        mtime = abs_path.stat().st_mtime if abs_path.exists() else 0
        cache_key = f"list_{abs_path}"
        if cache_key in DIR_CACHE and DIR_CACHE[cache_key]['mtime'] == mtime:
            print(f"{C.DIM}   (Cache hit){C.RESET}")
            entries = DIR_CACHE[cache_key]['entries']
        else:
            entries = []
            if abs_path.is_dir():
                for p in abs_path.iterdir():
                    if p.name not in IGNORE_DIRS:
                        entries.append(str(p))
            entries.sort()
            DIR_CACHE[cache_key] = {'mtime': mtime, 'entries': entries}
            
        for e in entries:
            icon = "📁" if Path(e).is_dir() else "📄"
            print(f"   {icon}  {C.DIM}{e}{C.RESET}")
            
        elapsed = time.time() - start_time
        print(f"{C.GREEN}✔ Done ({elapsed:.2f}s){C.RESET}")
        return entries
    except Exception as e:
        print(f"{C.RED}✘ Error: {e}{C.RESET}")
        return [f"ERROR listing {path}: {e}"]

@tool
def find_files(pattern: str, root: str = ".") -> List[str]:
    """Find files matching a glob pattern."""
    start_time = time.time()
    try:
        abs_root = _validate_path(root)
        _banner("SEARCH", C.BLUE, abs_root)
        print(f"   {C.DIM}Pattern: {pattern}{C.RESET}")
        
        mtime = abs_root.stat().st_mtime if abs_root.exists() else 0
        cache_key = f"find_{abs_root}_{pattern}"
        if cache_key in DIR_CACHE and DIR_CACHE[cache_key]['mtime'] == mtime:
            print(f"{C.DIM}   (Cache hit){C.RESET}")
            results = DIR_CACHE[cache_key]['results']
        else:
            results = []
            for p in abs_root.rglob(pattern):
                # Check against ignore dirs
                rel_parts = p.relative_to(abs_root).parts
                if not any(part in IGNORE_DIRS for part in rel_parts):
                    results.append(str(p))
            results.sort()
            DIR_CACHE[cache_key] = {'mtime': mtime, 'results': results}

        print(f"   {C.GREEN}{len(results)} match(es) found{C.RESET}")
        for r in results:
            print(f"   {C.DIM}→ {r}{C.RESET}")
            
        elapsed = time.time() - start_time
        print(f"{C.GREEN}✔ Done ({elapsed:.2f}s){C.RESET}")
        return results
    except Exception as e:
        print(f"{C.RED}✘ Error: {e}{C.RESET}")
        return [f"ERROR finding files in {root}: {e}"]

# ── Search ─────────────────────────────────────────────────────────────────────

@tool
def search_in_files(query: str, root: str = ".") -> List[str]:
    """Search for text inside files. Returns matching file paths."""
    start_time = time.time()
    try:
        abs_root = _validate_path(root)
        _banner("SEARCH", C.CYAN, abs_root)
        print(f"   {C.DIM}Query: \"{query}\"{C.RESET}")
        
        matches = []
        for file in abs_root.rglob("*"):
            if not file.is_file():
                continue
                
            rel_parts = file.relative_to(_get_agent_dir()).parts
            if any(part in IGNORE_DIRS for part in rel_parts):
                continue
                
            if _is_binary(file):
                continue
                
            if file.stat().st_size > MAX_FILE_SIZE:
                continue
                
            try:
                text = file.read_text(encoding="utf-8", errors="ignore")
                if query in text:
                    matches.append(str(file))
                    print(f"   {C.GREEN}✔ {file}{C.RESET}")
                    if len(matches) >= 100:
                        print(f"   {C.YELLOW}⚠ Reached 100 matches limit.{C.RESET}")
                        break
            except Exception:
                pass
                
        if not matches:
            print(f"   {C.YELLOW}No matches found{C.RESET}")
            
        elapsed = time.time() - start_time
        print(f"{C.GREEN}✔ Done ({elapsed:.2f}s){C.RESET}")
        return matches
    except Exception as e:
        print(f"{C.RED}✘ Error: {e}{C.RESET}")
        return [f"ERROR searching in {root}: {e}"]

# ── Terminal ───────────────────────────────────────────────────────────────────

@tool
def run_command(command: str, cwd: str = ".") -> str:
    """Execute a shell command."""
    start_time = time.time()
    try:
        abs_cwd = _validate_path(cwd)
        _banner("RUN", C.MAGENTA, abs_cwd)

        if _is_blocked(command):
            msg = (
                f"BLOCKED: '{command}' contains blocked patterns and cannot "
                f"be run by the agent."
            )
            print(f"{C.RED}✘ {msg}{C.RESET}")
            return msg

        print(f"   {C.BOLD}$ {command}{C.RESET}")
        _divider(C.DIM)

        result = subprocess.run(
            command,
            shell=True,
            cwd=abs_cwd,
            capture_output=True,
            text=True,
            input="y\n",
            timeout=60,
        )
        
        stdout_lines = result.stdout.strip().splitlines()
        stderr_lines = result.stderr.strip().splitlines()
        
        truncated = False
        if len(stdout_lines) > 200:
            stdout_lines = stdout_lines[:200]
            stdout_lines.append("... OUTPUT TRUNCATED ...")
            truncated = True
        if len(stderr_lines) > 200:
            stderr_lines = stderr_lines[:200]
            stderr_lines.append("... OUTPUT TRUNCATED ...")
            truncated = True
            
        stdout_text = "\n".join(stdout_lines)
        stderr_text = "\n".join(stderr_lines)

        if stdout_text:
            print(f"{C.DIM}{stdout_text}{C.RESET}")
        if stderr_text:
            print(f"{C.RED}{stderr_text}{C.RESET}")
            
        color = C.GREEN if result.returncode == 0 else C.RED
        print(f"{color}   Exit code: {result.returncode}{C.RESET}")
        
        elapsed = time.time() - start_time
        print(f"{color}✔ Done ({elapsed:.2f}s){C.RESET}")
        
        return (
            f"Exit Code: {result.returncode}\n\n"
            f"STDOUT:\n{stdout_text}\n\n"
            f"STDERR:\n{stderr_text}"
        )
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        msg = f"TimeoutExpired: Command killed after 60s."
        print(f"{C.YELLOW}   ⚠ {msg} ({elapsed:.2f}s){C.RESET}")
        return msg
    except Exception as e:
        print(f"{C.RED}✘ Error: {e}{C.RESET}")
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
    start_time = time.time()
    _banner("PREVIEW", C.YELLOW)
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
    elapsed = time.time() - start_time
    print(f"{C.GREEN}✔ Done ({elapsed:.2f}s){C.RESET}")
    return "\n".join(diff)

# ── Web Search ─────────────────────────────────────────────────────────────────

from serpapi import GoogleSearch

@tool
def search_web(query: str, num_results: int = 5) -> str:
    """Search Google using SerpAPI and return formatted results."""
    start_time = time.time()
    try:
        _banner("SEARCH", C.CYAN)
        print(f"   {C.DIM}Query: \"{query}\"{C.RESET}")
        api_key = os.getenv("SERPAPI_API_KEY")
        if not api_key:
            return "ERROR: SERPAPI_API_KEY environment variable not found."

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

        elapsed = time.time() - start_time
        print(f"{C.GREEN}✔ Done ({elapsed:.2f}s){C.RESET}")
        return "\n".join(output)
    except Exception as e:
        print(f"{C.RED}✘ Error: {e}{C.RESET}")
        return f"ERROR during web search: {e}"

# ── Ask User ───────────────────────────────────────────────────────────────────

@tool
def ask_user(question: str) -> str:
    """Ask the user for clarification and wait for a response."""
    _divider(C.CYAN)
    print(f"{C.CYAN}{C.BOLD}🤖 Agent needs your input{C.RESET}")
    _divider(C.CYAN)
    print(f"{C.WHITE}{question}{C.RESET}")
    _divider(C.DIM)
    response = input(f"{C.CYAN}Your response: {C.RESET}").strip()
    while not response:
        response = input(f"{C.YELLOW}Please enter a response: {C.RESET}").strip()
    return response

