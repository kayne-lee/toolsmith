# toolsmith

An optimizer and benchmark for MCP tool surfaces: it rewrites any MCP server's
tool descriptions and schemas from usage data, and measures whether that made it
better.

The optimizer works through a proxy that sits between the client and the target
server, records every call, and serves the target's tools with optimized
definitions laid over the originals. The target server is never modified, so it
can be one you did not write.

## The claim, and why it needs a benchmark

"Self-improving" is a phrase that usually means nothing. Something changes, the
output looks different, and nobody can say whether it improved. This repository
is organized to make that failure impossible: the benchmark is built before the
optimizer, results are reported on tasks never used for optimization, and every
proposed change is kept only if it survives measurement.

The headline number is tool-selection accuracy on a held-out task set, before
and after optimization. If that number does not move, the project's finding is
that this approach does not work — which is a result, and it gets reported as
one.

## The reference target

A tool surface needs to be real to be worth optimizing, and developing against
someone else's server leaves nothing under control. So `toolsmith` ships its own
test subject, a **codebase intelligence** server over a Git repository:

| Tool | Purpose |
|---|---|
| `search_code` | Content search with path and language filters |
| `read_file` | File contents, optionally a line range |
| `find_symbol` | Locate a definition by name |
| `find_references` | Where a symbol is used |
| `trace_dependencies` | Import graph traversal, either direction (Python) |
| `search_commits` | Commit history by message, author, or path |
| `blame_range` | Who last changed a line range, and in which commit |

Seven tools with genuinely overlapping purposes — `search_code`, `find_symbol`,
and `find_references` are all "find where a thing is", which is exactly the
ambiguity that makes tool selection hard and therefore worth optimizing.

The optimizer reaches this server only over the MCP protocol, as it would any
third-party server, and never imports its code.

## The three optimizations

**Description rewriting.** Telemetry records every call: which tool, what
arguments, whether it succeeded, and how it failed. A tool that is frequently
selected for tasks it cannot serve has a description that overclaims; a tool
that is passed over for tasks it handles well has one that underclaims. Both are
rewritten, re-benchmarked, and kept only on improvement.

**Schema tightening.** Parameters that models consistently malform — free-text
where an enum belongs, an ambiguous date format, a path that should be
repo-relative — get constrained so the mistake becomes unrepresentable rather
than merely discouraged.

**Macro synthesis.** When telemetry shows a call chain recurring — `find_symbol`
→ `read_file` → `find_references`, over and over — a single composite tool is
proposed for it. Fewer round trips, less context consumed, fewer chances to pick
wrong.

## What this deliberately does not do

**It does not generate or register executable tool code.** A server that writes
new code for itself and then runs it is a much more interesting demo and a
genuinely worse idea: arbitrary generation plus execution, in the component an
agent is trusting. Descriptions, schemas, and composition of *existing*
implementations get the result without that.

## Seeing it

`toolsmith ui` starts a local web frontend. It is built early and grows with
each milestone, so it shows the project's progress as well as the results. It
shows a target's tool surface and what optimization did to it: which tools get confused with which, how each
tool fails, every proposed change as a diff with its before/after numbers, and
whether it was kept. It reads the run records the benchmark and optimizer write
and changes nothing.

## Measuring

`bench/` holds a task suite split into a development half and a held-out half.
Optimization only ever sees development tasks. Reported numbers only ever come
from the held-out half. Overfitting a benchmark and calling it self-improvement
is the failure mode this project exists to avoid.

## Stack

Python 3.12, the official MCP Python SDK, `claude-opus-5` with adaptive thinking
for rewriting and for benchmark scoring.

## Install

```bash
uv sync
uv run pytest
```

Run the reference target over stdio, pointed at any Git repository:

```bash
uv run toolsmith reference --repo /path/to/repo
```

Serving the tools needs only a Git repository to point at. Optimization and
benchmarking need `ANTHROPIC_API_KEY`.

## Status

Under active development. See `PLAN.md` for the milestone breakdown and
`PROGRESS.md` for the running log.

## License

MIT
