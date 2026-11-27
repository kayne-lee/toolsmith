"""Command-line entry point: `toolsmith <command>`."""

from __future__ import annotations

import argparse
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="toolsmith")
    commands = parser.add_subparsers(dest="command", required=True)

    reference = commands.add_parser(
        "reference",
        help="run the reference target MCP server over stdio",
    )
    reference.add_argument(
        "--repo", default=".", help="Git repository to serve (default: current directory)"
    )

    args = parser.parse_args(argv)
    if args.command == "reference":
        # Imported here so the optimizer-side commands added later never load it.
        from toolsmith.reference.server import serve

        serve(args.repo)


if __name__ == "__main__":
    main()
