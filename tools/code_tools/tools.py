
from pathlib import Path
import subprocess
import difflib
from typing import List


# ---------- File Operations ----------

def read_file(path: str) -> str:
    """Read and return the contents of a file."""
    return Path(path).read_text(encoding="utf-8")


def create_file(path: str, content: str) -> str:
    """Create a new file with the given content."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Created {path}"


def overwrite_file(path: str, content: str) -> str:
    """Completely overwrite an existing file."""
    Path(path).write_text(content, encoding="utf-8")
    return f"Updated {path}"


def edit_file(path: str, old: str, new: str) -> str:
    """
    Replace the first occurrence of 'old' with 'new'.
    Useful for targeted edits instead of rewriting whole files.
    """
    p = Path(path)
    content = p.read_text(encoding="utf-8")

    if old not in content:
        raise ValueError("Target text not found.")

    content = content.replace(old, new, 1)
    p.write_text(content, encoding="utf-8")

    return f"Edited {path}"


def delete_file(path: str) -> str:
    """Delete a file."""
    Path(path).unlink(missing_ok=True)
    return f"Deleted {path}"


# ---------- Directory Operations ----------

def list_dir(path: str = ".") -> List[str]:
    """List files and directories."""
    return sorted([str(p) for p in Path(path).iterdir()])


def find_files(pattern: str, root: str = ".") -> List[str]:
    """
    Find files matching a glob pattern.

    Example:
        find_files("*.py")
        find_files("**/*.java")
    """
    return [str(p) for p in Path(root).glob(pattern)]


# ---------- Search ----------

def search_in_files(query: str, root: str = ".") -> List[str]:
    """
    Search for text inside files.
    Returns matching file paths.
    """
    matches = []

    for file in Path(root).rglob("*"):
        if file.is_file():
            try:
                text = file.read_text(encoding="utf-8", errors="ignore")
                if query in text:
                    matches.append(str(file))
            except Exception:
                pass

    return matches


# ---------- Terminal ----------

def run_command(command: str, cwd: str = ".") -> str:
    """Execute a shell command."""
    result = subprocess.run(
        command,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True,
    )

    return (
        f"Exit Code: {result.returncode}\n\n"
        f"STDOUT:\n{result.stdout}\n\n"
        f"STDERR:\n{result.stderr}"
    )


# ---------- Git ----------

def git_diff(cwd: str = ".") -> str:
    """Return current git diff."""
    return run_command("git diff", cwd)


# ---------- Testing ----------

def run_tests(command: str = "pytest", cwd: str = ".") -> str:
    """Run project tests."""
    return run_command(command, cwd)


# ---------- Diff Preview ----------

def preview_changes(old: str, new: str) -> str:
    """Generate a unified diff without modifying files."""
    diff = difflib.unified_diff(
        old.splitlines(),
        new.splitlines(),
        fromfile="before",
        tofile="after",
        lineterm="",
    )
    return "\n".join(diff)


from serpapi import GoogleSearch


def search_web(query: str, num_results: int = 5) -> str:
    """
    Search Google using SerpAPI and return formatted results.

    Requires:
        export SERPAPI_API_KEY="your_api_key"
    """

    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        raise ValueError("SERPAPI_API_KEY environment variable not found.")

    search = GoogleSearch(
        {
            "q": query,
            "api_key": api_key,
            "engine": "google",
            "num": num_results,
        }
    )

    results = search.get_dict()

    organic_results = results.get("organic_results", [])

    if not organic_results:
        return "No search results found."

    output = []

    for i, result in enumerate(organic_results, 1):
        title = result.get("title", "")
        link = result.get("link", "")
        snippet = result.get("snippet", "")

        output.append(
            f"{i}. {title}\n"
            f"URL: {link}\n"
            f"Snippet: {snippet}\n"
        )

    return "\n".join(output)





def ask_user(question: str) -> str:
     """ Ask the user for clarification and wait for a response. Examples: - Which framework should I use? - Should authentication use JWT or sessions? - Do you want PostgreSQL or SQLite? """ 
     print("\n" + "=" * 50)
     print("🤖 AGENT NEEDS YOUR INPUT")
     print("=" * 50)
     print(question)
     print("-" * 50)
     response = input("Your response: ").strip()
     while not response: response = input("Please enter a response: ").strip()
     return response
