"""A small Git repository with known contents and history, for exact assertions."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

FILES_V1 = {
    "pkg/__init__.py": "",
    "pkg/core.py": (
        "import json\n"
        "\n"
        "\n"
        "class Engine:\n"
        "    def run(self) -> str:\n"
        "        return json.dumps({'ok': True})\n"
        "\n"
        "\n"
        "LIMIT = 10\n"
    ),
    "pkg/cli.py": (
        "from pkg.core import Engine\n"
        "from . import util\n"
        "\n"
        "\n"
        "def main() -> None:\n"
        "    print(Engine().run(), util.helper())\n"
    ),
    "pkg/util.py": "def helper() -> int:\n    return 1\n",
    "web/app.ts": "export function render(): string {\n  return 'Engine';\n}\n",
    "README.md": "# Fixture\n\nThe Engine runs things.\n",
}


def _git(repo: Path, *args: str, date: str) -> None:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Ada",
        "GIT_AUTHOR_EMAIL": "ada@example.invalid",
        "GIT_COMMITTER_NAME": "Ada",
        "GIT_COMMITTER_EMAIL": "ada@example.invalid",
        "GIT_AUTHOR_DATE": date,
        "GIT_COMMITTER_DATE": date,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
    }
    subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True)


@pytest.fixture(scope="session")
def fixture_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    repo = tmp_path_factory.mktemp("fixture")
    _git(repo, "init", "-q", "-b", "main", date="2025-01-01T00:00:00Z")
    for rel, text in FILES_V1.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text)
    _git(repo, "add", "-A", date="2025-01-01T00:00:00Z")
    _git(repo, "commit", "-q", "-m", "add engine", date="2025-01-01T00:00:00Z")

    (repo / "pkg/util.py").write_text("def helper() -> int:\n    return 2\n")
    _git(repo, "add", "-A", date="2025-03-01T00:00:00Z")
    _git(repo, "commit", "-q", "-m", "bump helper value", date="2025-03-01T00:00:00Z")

    (repo / ".gitignore").write_text("ignored/\n")
    (repo / "ignored").mkdir()
    (repo / "ignored/secret.py").write_text("class Engine:\n    pass\n")
    _git(repo, "add", ".gitignore", date="2025-04-01T00:00:00Z")
    _git(repo, "commit", "-q", "-m", "ignore scratch", date="2025-04-01T00:00:00Z")
    return repo
