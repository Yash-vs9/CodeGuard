
from pathlib import Path
import subprocess
import difflib
from langchain.tools import tool
from typing import List


# ---------- File Operations ----------
@tool
def read_file(path: str) -> str:
    """Read and return the contents of a file."""
    print("reading file")
    return Path(path).read_text(encoding="utf-8")

@tool
def create_file(path: str, content: str) -> str:
    """Create a new file with the given content."""
    print("creating file")
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Created {path}"

@tool
def overwrite_file(path: str, content: str) -> str:
    """Completely overwrite an existing file."""
    print("overwriting file")
    Path(path).write_text(content, encoding="utf-8")
    return f"Updated {path}"

@tool
def edit_file(path: str, old: str, new: str) -> str:
    """
    Replace the first occurrence of 'old' with 'new'.
    Useful for targeted edits instead of rewriting whole files.
    """
    print("edit file")
    p = Path(path)
    content = p.read_text(encoding="utf-8")

    if old not in content:
        raise ValueError("Target text not found.")

    content = content.replace(old, new, 1)
    p.write_text(content, encoding="utf-8")

    return f"Edited {path}"

@tool
def delete_file(path: str) -> str:
    """Delete a file."""
    print("delete file")
    Path(path).unlink(missing_ok=True)
    return f"Deleted {path}"


# ---------- Directory Operations ----------

@tool
def list_dir(path: str = ".") -> List[str]:
    """List files and directories."""
    print("list dir")
    return sorted([str(p) for p in Path(path).iterdir()])


@tool
def find_files(pattern: str, root: str = ".") -> List[str]:
    """
    Find files matching a glob pattern.

    Example:
        find_files("*.py")
        find_files("**/*.java")
    """
    print("find files")
    return [str(p) for p in Path(root).glob(pattern)]


# ---------- Search ----------

@tool
def search_in_files(query: str, root: str = ".") -> List[str]:
    """
    Search for text inside files.
    Returns matching file paths.
    """
    matches = []
    print("search in files")
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

@tool
def run_command(command: str, cwd: str = ".") -> str:
    """Execute a shell command."""
    print("run commands")
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

@tool
def git_diff(cwd: str = ".") -> str:
    """Return current git diff."""
    return run_command("git diff", cwd)


# ---------- Testing ----------

@tool
def run_tests(command: str = "pytest", cwd: str = ".") -> str:
    """Run project tests."""
    return run_command(command, cwd)


# ---------- Diff Preview ----------

@tool
def preview_changes(old: str, new: str) -> str:
    """Generate a unified diff without modifying files."""
    print("prev changes")
    diff = difflib.unified_diff(
        old.splitlines(),
        new.splitlines(),
        fromfile="before",
        tofile="after",
        lineterm="",
    )
    return "\n".join(diff)


from serpapi import GoogleSearch

@tool
def search_web(query: str, num_results: int = 5) -> str:
    """
    Search Google using SerpAPI and return formatted results.

    Requires:
        export SERPAPI_API_KEY="your_api_key"
    """
    print("google calling")
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





@tool
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
