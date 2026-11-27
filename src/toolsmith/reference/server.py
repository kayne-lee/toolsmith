"""The reference target: an MCP server over one Git repository.

The descriptions and schemas here are deliberately naive first drafts — terse,
overlapping, and loose about argument formats. They are the "before" the
optimizer has to improve on, so do not polish them: a strong starting surface
would hide whatever effect optimization has. Changes to the surface belong in
the proxy's overrides (milestone 4 onward), never in this file.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from toolsmith import __version__
from toolsmith.reference.repo import Repo, RepoError

# Tool name → first-draft description. Kept in one table so the starting
# surface can be read, and diffed against optimized versions, at a glance.
DESCRIPTIONS: dict[str, str] = {
    "search_code": "Search the code.",
    "read_file": "Read a file.",
    "find_symbol": "Find a symbol.",
    "find_references": "Find references.",
    "trace_dependencies": "Trace dependencies.",
    "search_commits": "Search commits.",
    "blame_range": "Blame lines.",
}


def build_server(repo_path: str | Path) -> MCPServer:
    repo = Repo.open(repo_path)
    server: MCPServer = MCPServer(
        name="toolsmith-reference",
        version=__version__,
        instructions=f"Codebase tools for the Git repository at {repo.root.name}.",
    )

    def search_code(
        query: str,
        path: str | None = None,
        language: str | None = None,
        regex: bool = False,
        case_sensitive: bool = False,
        max_results: int = 50,
    ) -> dict[str, Any]:
        return repo.search_code(query, path, language, regex, case_sensitive, max_results)

    def read_file(
        path: str, start_line: int | None = None, end_line: int | None = None
    ) -> dict[str, Any]:
        return repo.read_file(path, start_line, end_line)

    def find_symbol(name: str, language: str | None = None) -> dict[str, Any]:
        return repo.find_symbol(name, language)

    def find_references(
        name: str, path: str | None = None, max_results: int = 100
    ) -> dict[str, Any]:
        return repo.find_references(name, path, max_results)

    def trace_dependencies(path: str, direction: str = "imports", depth: int = 1) -> dict[str, Any]:
        return repo.trace_dependencies(path, direction, depth)

    def search_commits(
        query: str | None = None,
        author: str | None = None,
        path: str | None = None,
        since: str | None = None,
        max_results: int = 20,
    ) -> dict[str, Any]:
        return repo.search_commits(query, author, path, since, max_results)

    def blame_range(path: str, start_line: int, end_line: int) -> dict[str, Any]:
        return repo.blame_range(path, start_line, end_line)

    for fn in (
        search_code,
        read_file,
        find_symbol,
        find_references,
        trace_dependencies,
        search_commits,
        blame_range,
    ):
        server.add_tool(
            _reporting_errors(fn), name=fn.__name__, description=DESCRIPTIONS[fn.__name__]
        )
    return server


def _reporting_errors(fn: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
    """Turn a RepoError into a ToolError, so the model sees why the call failed.

    The SDK hides the text of any other exception. A model that is told only
    "error" cannot recover, and the telemetry later needs the reason to classify
    the failure.
    """

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return fn(*args, **kwargs)
        except RepoError as exc:
            raise ToolError(str(exc)) from exc

    return wrapper


def serve(repo_path: str | Path) -> None:
    """Run the reference target over stdio until the client disconnects."""
    build_server(repo_path).run("stdio")
