"""The seven codebase-intelligence operations, over one Git repository.

Plain Python with no MCP in it, so the behaviour can be tested directly and the
server module stays a thin layer of names and descriptions over it.

Everything shells out to `git` rather than walking the filesystem, so results
cover tracked and new-but-not-ignored files and respect `.gitignore` the way a
person would expect.
"""

from __future__ import annotations

import ast
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

LANGUAGE_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "python": (".py", ".pyi"),
    "javascript": (".js", ".jsx", ".mjs", ".cjs"),
    "typescript": (".ts", ".tsx"),
    "go": (".go",),
    "rust": (".rs",),
    "java": (".java",),
    "markdown": (".md",),
    "yaml": (".yml", ".yaml"),
    "toml": (".toml",),
}

# Definition patterns per language, as extended regular expressions with a
# `NAME` placeholder. Regex rather than a parser per language: good enough to
# find a definition, and the optimizer cares about which tool gets picked, not
# about this tool being a perfect indexer.
_DEFINITION_PATTERNS: dict[str, tuple[str, ...]] = {
    "python": (
        r"^\s*(async\s+)?def\s+NAME\b",
        r"^\s*class\s+NAME\b",
        r"^NAME\s*(:[^=]*)?=",
    ),
    "javascript": (
        r"^\s*(export\s+)?(default\s+)?(async\s+)?function\s*\*?\s*NAME\b",
        r"^\s*(export\s+)?(default\s+)?class\s+NAME\b",
        r"^\s*(export\s+)?(const|let|var)\s+NAME\b",
    ),
    "go": (r"^func\s+(\([^)]*\)\s*)?NAME\b", r"^type\s+NAME\b"),
    "rust": (r"^\s*(pub(\([^)]*\))?\s+)?(fn|struct|enum|trait|type)\s+NAME\b",),
    "java": (
        r"^\s*(public|private|protected)?\s*(static\s+)?(final\s+)?(class|interface|enum)\s+NAME\b",
    ),
}
_DEFINITION_PATTERNS["typescript"] = (
    *_DEFINITION_PATTERNS["javascript"],
    r"^\s*(export\s+)?(interface|type|enum)\s+NAME\b",
)

_IDENTIFIER = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")


class RepoError(ValueError):
    """A request the repository cannot serve: bad path, bad range, bad argument."""


@dataclass(frozen=True, slots=True)
class Repo:
    root: Path

    @classmethod
    def open(cls, path: str | Path) -> Repo:
        top = _git(Path(path), "rev-parse", "--show-toplevel").strip()
        return cls(Path(top).resolve())

    # -- search_code ---------------------------------------------------------

    def search_code(
        self,
        query: str,
        path: str | None = None,
        language: str | None = None,
        regex: bool = False,
        case_sensitive: bool = False,
        max_results: int = 50,
    ) -> dict[str, Any]:
        if not query:
            raise RepoError("query must not be empty")
        args = ["grep", "-n", "-I", "--untracked", "--no-color", "-E" if regex else "-F"]
        if not case_sensitive:
            args.append("-i")
        args += ["-e", query, "--", *self._pathspecs(path, language)]
        out = _git(self.root, *args, ok_codes=(0, 1))
        matches = [_parse_grep_line(line) for line in out.splitlines()]
        return _limited("matches", matches, max_results)

    # -- read_file -----------------------------------------------------------

    def read_file(
        self, path: str, start_line: int | None = None, end_line: int | None = None
    ) -> dict[str, Any]:
        file = self._resolve(path)
        if not file.is_file():
            raise RepoError(f"not a file: {path}")
        lines = file.read_text(errors="replace").splitlines()
        start = 1 if start_line is None else start_line
        end = len(lines) if end_line is None else min(end_line, len(lines))
        if start < 1 or (lines and start > len(lines)) or end < start - 1:
            raise RepoError(f"line range {start}-{end} is outside 1-{len(lines)} for {path}")
        return {
            "path": self._relative(file),
            "start_line": start,
            "end_line": end,
            "total_lines": len(lines),
            "content": "\n".join(lines[start - 1 : end]),
        }

    # -- find_symbol ---------------------------------------------------------

    def find_symbol(self, name: str, language: str | None = None) -> dict[str, Any]:
        _require_identifier(name)
        languages = [language] if language else list(_DEFINITION_PATTERNS)
        found: list[dict[str, Any]] = []
        for lang in languages:
            patterns = _DEFINITION_PATTERNS.get(lang)
            if patterns is None:
                raise RepoError(f"unsupported language: {lang}")
            # git narrows to lines containing the word; Python's `re` decides
            # which are definitions, since git's own regex dialect varies by build.
            definition = re.compile(
                "|".join(f"(?:{p.replace('NAME', re.escape(name))})" for p in patterns)
            )
            out = _git(
                self.root,
                "grep", "-n", "-I", "-w", "-F", "--untracked", "--no-color", "-e", name,
                "--", *self._pathspecs(None, lang),
                ok_codes=(0, 1),
            )  # fmt: skip
            for line in out.splitlines():
                match = _parse_grep_line(line)
                if definition.search(match["text"]):
                    match["language"] = lang
                    found.append(match)
        return {"name": name, "definitions": found}

    # -- find_references -----------------------------------------------------

    def find_references(
        self, name: str, path: str | None = None, max_results: int = 100
    ) -> dict[str, Any]:
        _require_identifier(name)
        definitions = {(d["path"], d["line"]) for d in self.find_symbol(name)["definitions"]}
        out = _git(
            self.root,
            "grep", "-n", "-I", "-w", "-F", "--untracked", "--no-color", "-e", name,
            "--", *self._pathspecs(path, None),
            ok_codes=(0, 1),
        )  # fmt: skip
        refs = [
            m
            for m in (_parse_grep_line(line) for line in out.splitlines())
            if (m["path"], m["line"]) not in definitions
        ]
        return _limited("references", refs, max_results)

    # -- trace_dependencies --------------------------------------------------

    def trace_dependencies(
        self, path: str, direction: str = "imports", depth: int = 1
    ) -> dict[str, Any]:
        """Python import graph, from a file outward or inward.

        `imports` follows what the file imports; `imported_by` follows what
        imports it. Only modules inside the repository are traversed; external
        imports are reported but not followed.
        """
        if direction not in ("imports", "imported_by"):
            raise RepoError("direction must be 'imports' or 'imported_by'")
        if depth < 1:
            raise RepoError("depth must be at least 1")
        start = self._relative(self._resolve(path))
        if not start.endswith(".py"):
            raise RepoError("trace_dependencies supports Python files only")

        modules = self._python_modules()
        graph = {file: self._imports_of(file, modules) for file in modules.values()}
        edges_of: dict[str, tuple[list[str], list[str]]]
        if direction == "imported_by":
            reverse: dict[str, set[str]] = {file: set() for file in graph}
            for file, (targets, _) in graph.items():
                for target in targets:
                    reverse[target].add(file)
            edges_of = {f: (sorted(targets), []) for f, targets in reverse.items()}
        else:
            edges_of = {f: (sorted(i), sorted(e)) for f, (i, e) in graph.items()}

        if start not in edges_of:
            raise RepoError(f"not a tracked Python file: {path}")
        edges: list[dict[str, Any]] = []
        external: set[str] = set()
        seen = {start}
        frontier = [start]
        for level in range(1, depth + 1):
            next_frontier: list[str] = []
            for file in frontier:
                internal_targets, ext = edges_of[file]
                external.update(ext)
                for target in internal_targets:
                    edges.append({"from": file, "to": target, "depth": level})
                    if target not in seen:
                        seen.add(target)
                        next_frontier.append(target)
            frontier = next_frontier
        return {
            "path": start,
            "direction": direction,
            "depth": depth,
            "edges": edges,
            "external": sorted(external),
        }

    # -- search_commits ------------------------------------------------------

    def search_commits(
        self,
        query: str | None = None,
        author: str | None = None,
        path: str | None = None,
        since: str | None = None,
        max_results: int = 20,
    ) -> dict[str, Any]:
        sep, end = "\x1f", "\x1e"
        args = [
            "log",
            f"--max-count={max_results + 1}",
            f"--format=%H{sep}%an{sep}%aI{sep}%s{end}",
            "-i",
        ]
        if query:
            args.append(f"--grep={query}")
        if author:
            args.append(f"--author={author}")
        if since:
            args.append(f"--since={since}")
        if path:
            args += ["--", self._relative(self._resolve(path, must_exist=False))]
        out = _git(self.root, *args)
        commits = []
        for record in out.split(end):
            record = record.strip()
            if record:
                sha, name, date, subject = record.split(sep, 3)
                commits.append({"sha": sha, "author": name, "date": date, "subject": subject})
        return _limited("commits", commits, max_results)

    # -- blame_range ---------------------------------------------------------

    def blame_range(self, path: str, start_line: int, end_line: int) -> dict[str, Any]:
        rel = self._relative(self._resolve(path))
        if start_line < 1 or end_line < start_line:
            raise RepoError(f"invalid line range {start_line}-{end_line}")
        try:
            out = _git(
                self.root, "blame", "--porcelain", "-L", f"{start_line},{end_line}", "--", rel
            )
        except RepoError as exc:
            raise RepoError(f"cannot blame {rel} lines {start_line}-{end_line}: {exc}") from None
        return {"path": rel, "lines": _parse_porcelain_blame(out)}

    # -- helpers -------------------------------------------------------------

    def _resolve(self, path: str, *, must_exist: bool = True) -> Path:
        candidate = (self.root / path).resolve()
        if not candidate.is_relative_to(self.root):
            raise RepoError(f"path is outside the repository: {path}")
        if must_exist and not candidate.exists():
            raise RepoError(f"no such path: {path}")
        return candidate

    def _relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix() or "."

    def _pathspecs(self, path: str | None, language: str | None) -> list[str]:
        base = self._relative(self._resolve(path)) if path else "."
        if language is None:
            return [base]
        extensions = LANGUAGE_EXTENSIONS.get(language.lower())
        if extensions is None:
            raise RepoError(f"unsupported language: {language}")
        prefix = "" if base == "." else f"{base.rstrip('/')}/"
        return [f":(glob){prefix}**/*{ext}" for ext in extensions]

    def _python_modules(self) -> dict[str, str]:
        """Dotted module name → repo-relative path, for every non-ignored .py file.

        Both `src/pkg/mod.py` and `pkg/mod.py` layouts are handled by also
        registering the name with a leading `src.` stripped.
        """
        files = _git(
            self.root, "ls-files", "--cached", "--others", "--exclude-standard", "--", "*.py"
        ).splitlines()
        modules: dict[str, str] = {}
        for file in files:
            parts = file[:-3].split("/")
            if parts[-1] == "__init__":
                parts = parts[:-1]
            if not parts:
                continue
            modules[".".join(parts)] = file
            if parts[0] == "src" and len(parts) > 1:
                modules[".".join(parts[1:])] = file
        return modules

    def _imports_of(self, file: str, modules: dict[str, str]) -> tuple[set[str], set[str]]:
        try:
            tree = ast.parse((self.root / file).read_text(errors="replace"), filename=file)
        except SyntaxError:
            return set(), set()
        package = _package_of(file, modules)
        internal: set[str] = set()
        external: set[str] = set()
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = _absolute_module(node.module, node.level, package)
                if base is None:
                    continue
                names = [base] + [f"{base}.{alias.name}" for alias in node.names]
            for name in names:
                target = _longest_module(name, modules)
                if target is not None:
                    if target != file:
                        internal.add(target)
                elif not isinstance(node, ast.ImportFrom) or node.level == 0:
                    external.add(name.split(".")[0])
        return internal, external


def _git(cwd: Path, *args: str, ok_codes: tuple[int, ...] = (0,)) -> str:
    result = subprocess.run(
        ["git", "-c", "core.quotepath=off", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in ok_codes:
        raise RepoError(result.stderr.strip() or f"git {args[0]} failed")
    return result.stdout


def _parse_grep_line(line: str) -> dict[str, Any]:
    path, number, text = line.split(":", 2)
    return {"path": path, "line": int(number), "text": text}


def _limited(key: str, items: list[dict[str, Any]], max_results: int) -> dict[str, Any]:
    if max_results < 1:
        raise RepoError("max_results must be at least 1")
    return {key: items[:max_results], "truncated": len(items) > max_results}


def _require_identifier(name: str) -> None:
    if not _IDENTIFIER.match(name):
        raise RepoError(f"not an identifier: {name!r}")


def _package_of(file: str, modules: dict[str, str]) -> str:
    names = [name for name, path in modules.items() if path == file]
    name = min(names, key=len) if names else ""
    return name if file.endswith("__init__.py") else name.rpartition(".")[0]


def _absolute_module(module: str | None, level: int, package: str) -> str | None:
    if level == 0:
        return module
    parts = package.split(".") if package else []
    if level - 1 > len(parts):
        return None
    base = parts[: len(parts) - (level - 1)]
    if module:
        base.append(module)
    return ".".join(base) or None


def _longest_module(name: str, modules: dict[str, str]) -> str | None:
    parts = name.split(".")
    while parts:
        file = modules.get(".".join(parts))
        if file is not None:
            return file
        parts.pop()
    return None


def _parse_porcelain_blame(out: str) -> list[dict[str, Any]]:
    commits: dict[str, dict[str, str]] = {}
    lines: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for raw in out.splitlines():
        if raw.startswith("\t"):
            info = commits[current["sha"]]
            lines.append({**current, **info, "text": raw[1:]})
            current = {}
        elif not current:
            sha, _, final_line, *_ = raw.split(" ")
            current = {"sha": sha, "line": int(final_line)}
            commits.setdefault(sha, {})
        else:
            key, _, value = raw.partition(" ")
            if key == "author":
                commits[current["sha"]]["author"] = value
            elif key == "author-time":
                when = datetime.fromtimestamp(int(value), UTC)
                commits[current["sha"]]["date"] = when.isoformat()
            elif key == "summary":
                commits[current["sha"]]["summary"] = value
    return lines
