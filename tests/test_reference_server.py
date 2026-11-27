"""The reference target over MCP: in-process against the fixture, and over stdio
against this repository, which is milestone 1's "Done when"."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any

from mcp import Client, StdioServerParameters

from toolsmith.reference.server import DESCRIPTIONS, build_server

ROOT = Path(__file__).resolve().parents[1]
TOOLS = set(DESCRIPTIONS)


async def call(client: Client, tool: str, args: dict[str, Any]) -> dict[str, Any]:
    result = await client.call_tool(tool, args)
    assert not result.is_error, result.content
    assert result.structured_content is not None
    return result.structured_content


async def test_lists_seven_tools_with_first_draft_surface(fixture_repo: Path) -> None:
    async with Client(build_server(fixture_repo)) as client:
        tools = (await client.list_tools()).tools
    assert {t.name for t in tools} == TOOLS
    for tool in tools:
        assert tool.description == DESCRIPTIONS[tool.name]
        assert tool.input_schema["type"] == "object"


async def test_tool_error_reaches_the_model_with_its_reason(fixture_repo: Path) -> None:
    async with Client(build_server(fixture_repo)) as client:
        result = await client.call_tool("read_file", {"path": "../escape"})
    assert result.is_error
    text = "".join(getattr(block, "text", "") for block in result.content)
    assert "outside the repository" in text


async def test_all_seven_tools_over_stdio_against_this_repository() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "toolsmith.cli", "reference", "--repo", str(ROOT)],
        cwd=str(ROOT),
    )
    async with Client(params) as client:
        assert {t.name for t in (await client.list_tools()).tools} == TOOLS

        hits = await call(client, "search_code", {"query": "publishing=True", "path": "src"})
        assert "src/toolsmith/bench/split.py" in {m["path"] for m in hits["matches"]}

        split = await call(client, "read_file", {"path": "src/toolsmith/bench/split.py"})
        assert "class Split(Enum):" in split["content"]

        definitions = await call(client, "find_symbol", {"name": "Split"})
        [definition] = definitions["definitions"]
        assert definition["path"] == "src/toolsmith/bench/split.py"
        line = definition["line"]
        assert split["content"].splitlines()[line - 1].startswith("class Split")

        refs = await call(client, "find_references", {"name": "HeldOutAccessError"})
        assert "tests/test_split.py" in {r["path"] for r in refs["references"]}

        deps = await call(
            client,
            "trace_dependencies",
            {"path": "src/toolsmith/bench/split.py", "direction": "imported_by"},
        )
        assert "tests/test_split.py" in {e["to"] for e in deps["edges"]}

        commits = await call(client, "search_commits", {"max_results": 5})
        assert commits["commits"], "this repository has history"

        blame = await call(
            client, "blame_range", {"path": "src/toolsmith/bench/split.py", "start_line": line,
                                    "end_line": line},
        )  # fmt: skip
        assert blame["lines"][0]["text"].startswith("class Split")


def test_optimizer_side_never_imports_the_reference_target() -> None:
    """The optimizer must treat the reference target as a third-party server.

    Only the CLI, which launches it, and the package itself may import it.
    """
    allowed = {"cli.py"}
    offenders = []
    package = ROOT / "src" / "toolsmith"
    for file in package.rglob("*.py"):
        rel = file.relative_to(package)
        if rel.parts[0] == "reference" or rel.as_posix() in allowed:
            continue
        for node in ast.walk(ast.parse(file.read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            if any(
                n == "toolsmith.reference" or n.startswith("toolsmith.reference.") for n in names
            ):
                offenders.append(rel.as_posix())
    assert offenders == []
