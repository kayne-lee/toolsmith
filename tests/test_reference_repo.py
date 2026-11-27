from __future__ import annotations

from pathlib import Path

import pytest

from toolsmith.reference.repo import Repo, RepoError


@pytest.fixture
def repo(fixture_repo: Path) -> Repo:
    return Repo.open(fixture_repo)


def paths(items: list[dict[str, object]]) -> list[object]:
    return [item["path"] for item in items]


# -- search_code --------------------------------------------------------------


def test_search_code_finds_text_and_ignores_gitignored(repo: Repo) -> None:
    result = repo.search_code("Engine")
    assert set(paths(result["matches"])) == {"pkg/core.py", "pkg/cli.py", "web/app.ts", "README.md"}
    assert not result["truncated"]


def test_search_code_language_filter(repo: Repo) -> None:
    result = repo.search_code("engine", language="typescript")
    assert paths(result["matches"]) == ["web/app.ts"]


def test_search_code_path_filter_and_regex(repo: Repo) -> None:
    result = repo.search_code(r"def [a-z]+\(", path="pkg", regex=True)
    assert set(paths(result["matches"])) == {"pkg/core.py", "pkg/cli.py", "pkg/util.py"}


def test_search_code_is_case_insensitive_by_default(repo: Repo) -> None:
    assert repo.search_code("ENGINE")["matches"]
    assert not repo.search_code("ENGINE", case_sensitive=True)["matches"]


def test_search_code_truncates(repo: Repo) -> None:
    result = repo.search_code("Engine", max_results=1)
    assert len(result["matches"]) == 1
    assert result["truncated"]


def test_search_code_rejects_unknown_language(repo: Repo) -> None:
    with pytest.raises(RepoError, match="unsupported language"):
        repo.search_code("x", language="cobol")


# -- read_file ----------------------------------------------------------------


def test_read_file_whole_and_range(repo: Repo) -> None:
    whole = repo.read_file("pkg/core.py")
    assert whole["total_lines"] == 9
    assert whole["content"].startswith("import json")
    part = repo.read_file("pkg/core.py", 4, 5)
    assert part["content"] == "class Engine:\n    def run(self) -> str:"


def test_read_file_clamps_end_past_eof(repo: Repo) -> None:
    assert repo.read_file("pkg/util.py", 2, 99)["end_line"] == 2


@pytest.mark.parametrize("bad", ["../outside.txt", "/etc/passwd"])
def test_read_file_refuses_paths_outside_repo(repo: Repo, bad: str) -> None:
    with pytest.raises(RepoError, match="outside the repository"):
        repo.read_file(bad)


def test_read_file_rejects_bad_range_and_missing_file(repo: Repo) -> None:
    with pytest.raises(RepoError, match="outside"):
        repo.read_file("pkg/util.py", 50, 60)
    with pytest.raises(RepoError, match="no such path"):
        repo.read_file("pkg/missing.py")


# -- find_symbol --------------------------------------------------------------


def test_find_symbol_class_function_constant(repo: Repo) -> None:
    assert [(d["path"], d["line"]) for d in repo.find_symbol("Engine")["definitions"]] == [
        ("pkg/core.py", 4)
    ]
    assert paths(repo.find_symbol("helper")["definitions"]) == ["pkg/util.py"]
    assert paths(repo.find_symbol("LIMIT")["definitions"]) == ["pkg/core.py"]


def test_find_symbol_other_languages(repo: Repo) -> None:
    [definition] = repo.find_symbol("render")["definitions"]
    assert definition["path"] == "web/app.ts"
    assert definition["language"] == "typescript"


def test_find_symbol_does_not_match_uses_or_prefixes(repo: Repo) -> None:
    assert repo.find_symbol("Eng")["definitions"] == []
    assert repo.find_symbol("main")["definitions"][0]["path"] == "pkg/cli.py"
    assert len(repo.find_symbol("main")["definitions"]) == 1


def test_find_symbol_rejects_non_identifier(repo: Repo) -> None:
    with pytest.raises(RepoError, match="not an identifier"):
        repo.find_symbol("Engine()")


# -- find_references ----------------------------------------------------------


def test_find_references_excludes_definitions(repo: Repo) -> None:
    refs = repo.find_references("Engine")["references"]
    assert ("pkg/core.py", 4) not in {(r["path"], r["line"]) for r in refs}
    assert {"pkg/cli.py", "web/app.ts", "README.md"} <= set(paths(refs))


def test_find_references_whole_word_only(repo: Repo) -> None:
    assert repo.find_references("Eng")["references"] == []


# -- trace_dependencies -------------------------------------------------------


def test_trace_imports_resolves_absolute_and_relative(repo: Repo) -> None:
    result = repo.trace_dependencies("pkg/cli.py")
    assert {e["to"] for e in result["edges"]} == {"pkg/core.py", "pkg/util.py", "pkg/__init__.py"}


def test_trace_imports_depth_two_reaches_external(repo: Repo) -> None:
    result = repo.trace_dependencies("pkg/cli.py", depth=2)
    assert "json" in result["external"]


def test_trace_imported_by(repo: Repo) -> None:
    result = repo.trace_dependencies("pkg/core.py", direction="imported_by")
    assert result["edges"] == [{"from": "pkg/core.py", "to": "pkg/cli.py", "depth": 1}]


def test_trace_rejects_bad_input(repo: Repo) -> None:
    with pytest.raises(RepoError, match="direction"):
        repo.trace_dependencies("pkg/cli.py", direction="sideways")
    with pytest.raises(RepoError, match="Python files only"):
        repo.trace_dependencies("web/app.ts")


# -- search_commits -----------------------------------------------------------


def test_search_commits_newest_first(repo: Repo) -> None:
    subjects = [c["subject"] for c in repo.search_commits()["commits"]]
    assert subjects == ["ignore scratch", "bump helper value", "add engine"]


def test_search_commits_filters(repo: Repo) -> None:
    by_message = repo.search_commits(query="HELPER")["commits"]
    assert [c["subject"] for c in by_message] == ["bump helper value"]
    by_path = repo.search_commits(path="pkg/util.py")["commits"]
    assert [c["subject"] for c in by_path] == ["bump helper value", "add engine"]
    since = repo.search_commits(since="2025-02-01")["commits"]
    assert [c["subject"] for c in since] == ["ignore scratch", "bump helper value"]
    assert repo.search_commits(author="nobody")["commits"] == []


# -- blame_range --------------------------------------------------------------


def test_blame_range_attributes_each_line(repo: Repo) -> None:
    lines = repo.blame_range("pkg/util.py", 1, 2)["lines"]
    assert [line["summary"] for line in lines] == ["add engine", "bump helper value"]
    assert lines[1]["text"] == "    return 2"
    assert lines[1]["author"] == "Ada"
    assert lines[1]["date"].startswith("2025-03-01")


def test_blame_range_rejects_bad_range(repo: Repo) -> None:
    with pytest.raises(RepoError):
        repo.blame_range("pkg/util.py", 5, 9)
    with pytest.raises(RepoError, match="invalid line range"):
        repo.blame_range("pkg/util.py", 2, 1)
