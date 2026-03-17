"""
Tool implementations for the debugging agents.

Both agents get the same tools:
  - read_file: read any file in the task/ directory
  - search_code: grep-like search across all .ts files
  - read_logs: read the application logs
  - read_test_results: read the test output
  - list_files: list all files in the task directory
"""

from pathlib import Path

TASK_DIR = Path(__file__).parent.parent / "task"

# Files agents are allowed to read
ALLOWED_FILES = {
    "discount.ts",
    "user.ts",
    "checkout.ts",
    "utils.ts",
    "config.ts",
    "middleware.ts",
    "cache.ts",
    "types.ts",
    "logs.txt",
    "test_results.txt",
    "bug_report.md",
}


def read_file(filename: str) -> str:
    """Read a file from the task directory."""
    filename = filename.strip().removeprefix("task/")
    if filename not in ALLOWED_FILES:
        return f"Error: file '{filename}' not found. Available files: {sorted(ALLOWED_FILES)}"
    path = TASK_DIR / filename
    content = path.read_text()
    # Add line numbers for reference
    lines = content.splitlines()
    numbered = [f"{i + 1:3d} | {line}" for i, line in enumerate(lines)]
    return f"=== {filename} ===\n" + "\n".join(numbered)


def search_code(query: str) -> str:
    """Search for a string across all TypeScript files in the task directory."""
    query_lower = query.lower()
    results = []
    for fname in sorted(ALLOWED_FILES):
        if not fname.endswith(".ts"):
            continue
        path = TASK_DIR / fname
        content = path.read_text()
        for i, line in enumerate(content.splitlines(), start=1):
            if query_lower in line.lower():
                results.append(f"{fname}:{i}  {line.strip()}")
    if not results:
        return f"No matches found for '{query}'"
    return f"Search results for '{query}':\n" + "\n".join(results)


def read_logs() -> str:
    """Read the application logs."""
    return read_file("logs.txt")


def read_test_results() -> str:
    """Read the test output."""
    return read_file("test_results.txt")


def list_files() -> str:
    """List all files available in the task directory."""
    files = sorted(ALLOWED_FILES)
    return "Files in task/:\n" + "\n".join(f"  - {f}" for f in files)


# Tool dispatch map
TOOL_DISPATCH = {
    "read_file": lambda args: read_file(args["filename"]),
    "search_code": lambda args: search_code(args["query"]),
    "read_logs": lambda _: read_logs(),
    "read_test_results": lambda _: read_test_results(),
    "list_files": lambda _: list_files(),
}


def execute_tool(name: str, arguments: dict) -> str:
    """Execute a tool by name with the given arguments."""
    handler = TOOL_DISPATCH.get(name)
    if not handler:
        return f"Error: unknown tool '{name}'"
    try:
        return handler(arguments)
    except Exception as e:
        return f"Error executing {name}: {e}"
