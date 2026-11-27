# Progress log

Append-only. Newest entry at the bottom.

The purpose of this file is continuity: a session that starts cold reads the last
entry and knows where the work stopped, what was decided, and what is blocked.
Record decisions and their reasons, not just what was written — the file list is
already in the git log.

Benchmark numbers go here every time they change, with the split they came from
labelled. A number without its split is not a result.

---

## Scaffold

Repository created. Structure, tooling, and CI in place; no server code yet.

**Decided:**
- Codebase intelligence as the served domain. The tool surface needs genuine
  selection ambiguity to be worth optimizing, and `search_code` /`find_symbol` /
  `find_references` overlap in exactly the way that produces it. It also
  dogfoods against this repository.
- The benchmark is milestones 1–2, before any optimization exists. Every claim
  here is a before-and-after.
- Development / held-out split enforced in code, not by discipline. The whole
  point of the project is not overfitting the measurement, so the measurement
  gets a guard rail.
- First-draft tool descriptions are deliberately naive. A strong starting
  surface would mask whatever effect the optimizer has.
- No generation of executable tool code. Descriptions, schemas, and composition
  of existing implementations only — a server that writes and runs new code for
  itself is a security problem, not a feature.

**Next:** Milestone 1, server and tool surface. See `PLAN.md`.

---

## Plan amendment: the optimizer is the product

No code changed. `PLAN.md` and `README.md` amended.

**Decided:**
- The optimizer and benchmark are the product and must work against any MCP
  server, including ones toolsmith cannot edit. The codebase-intelligence
  server is now the *reference target*: the test subject we control, not the
  deliverable.
- Optimizations are applied by an MCP proxy between client and target, which
  records calls and serves overridden descriptions, schemas, and macros. The
  target is never modified. Macros stay compositions of the target's existing
  tools, so the no-code-generation rule still holds.
- Milestone 3 becomes "Proxy and telemetry": telemetry is recorded in the proxy,
  not inside the server, so it works for third-party targets.
- Milestone 2's harness connects to a target as an MCP client from a launch
  command; task suites belong to a target.
- Milestone 7 adds a second, third-party MCP server with its own suite, as
  evidence the optimizer is not tuned to the reference target.
- The reference target's code must not be imported by the optimizer packages.

**Next:** Milestone 1, reference target server. See `PLAN.md`.

---

## Plan amendment: frontend

No code changed. `PLAN.md` and `README.md` amended.

**Decided:**
- A local web frontend (`toolsmith ui`) becomes milestone 7; results move to 8.
  The point of the project is a before-and-after, and people should be able to
  see it without reading logs.
- The frontend is read-only over structured records in `runs/`. Milestones 2–6
  each write their output there in a versioned format, so the frontend has data
  from the start and anything it shows is reproducible.
- The tool-confusion matrix (needed tool against picked tool) is the main view,
  since tool overlap is the problem the optimizer targets.
- Held-out numbers are hidden in the frontend until published, matching the
  guard on the split in code.
- UI framework not chosen yet; decide at milestone 7.

**Next:** Milestone 1, reference target server. See `PLAN.md`.

---

## Plan amendment: frontend moves to milestone 2

No code changed. `PLAN.md` amended. Supersedes the placement in the previous
entry, which put the frontend at milestone 7.

**Decided:**
- The frontend is milestone 2, right after the reference target, so development
  can be watched as it happens rather than only once it is finished.
- Milestone 2 builds the foundation: `toolsmith ui`, the versioned `runs/`
  record format, a project view (milestones, this log, benchmark numbers with
  their splits) and a tool surface view (a target's tools as `tools/list`
  reports them).
- Every later milestone adds the view for what it produces, and its "Done when"
  includes that view working: runs and tool confusion (3), failures (4),
  optimization history (5, extended in 6), macro tradeoff (7), held-out
  results (8).
- Milestones renumbered: benchmark 3, proxy and telemetry 4, description
  rewriting 5, schema tightening 6, macro synthesis 7, results 8.
- UI framework is chosen at milestone 2.

**Next:** Milestone 1, reference target server. See `PLAN.md`.


---

## Milestone 1 — Reference target server

Built `toolsmith.reference`: the seven codebase-intelligence tools over a Git
repository, served over stdio with `toolsmith reference --repo PATH`.

**Done-when check:** met. `tests/test_reference_server.py` launches the server
over stdio as a subprocess, connects with an MCP client, and calls all seven
tools against this repository, asserting each result is correct (for example,
`find_symbol("Split")` returns the line `read_file` shows as `class Split`).
34 tests pass; ruff, ruff format, and mypy strict are clean.

No benchmark numbers yet; the benchmark is milestone 3.

**Decided:**
- Operations live in `reference/repo.py` as plain Python with no MCP in it;
  `reference/server.py` is a thin layer of names and descriptions. The
  operations are tested directly against a fixture repository with fixed
  history (`tests/conftest.py`), so assertions are exact.
- First-draft descriptions are one line each ("Search the code.", "Find a
  symbol.") and kept in one `DESCRIPTIONS` table. Schemas are loose on purpose:
  `direction` and `since` are free strings, paths are unconstrained, no
  parameter has a description. This is the "before"; it must not be polished
  here. Changes belong in the proxy's overrides from milestone 4.
- Everything shells out to `git`, so results cover tracked and
  new-but-not-ignored files and respect `.gitignore`.
- `find_symbol` uses `git grep -w` to narrow, then per-language regexes in
  Python to decide which lines are definitions. git's regex dialect varies by
  build (`\s` and `\b` silently matched nothing), so matching is done in `re`.
  Supported: Python, JavaScript, TypeScript, Go, Rust, Java.
- `trace_dependencies` is a Python import graph in either direction
  (`imports`, `imported_by`) with a depth. **This narrows the README's original
  "import and call graph" to imports only.** A call graph is a large job on its
  own, and the import graph already gives the overlap with `find_references`
  that the benchmark needs. README updated to match. Revisit if milestone 3's
  tasks need call-level questions.
- Errors from the repository reach the model with their reason. The MCP 2.x SDK
  hides the text of any exception other than `ToolError`, so `RepoError` is
  converted. The model needs the reason to recover, and telemetry needs it to
  classify the failure.
- Moved to the MCP Python SDK 2.x (`MCPServer`, formerly `FastMCP`), pinned
  `mcp>=2.3,<3`.
- Removed the empty `server/` and `tools/` scaffold packages, which belonged to
  the earlier self-modifying design. The proxy will get its own package.
- A test enforces the plan's boundary: nothing in `src/toolsmith` outside
  `reference/` imports it, except `cli.py`, which launches it.

**Blocked:** nothing.

**Note:** the GitHub issues still carry the old seven-milestone titles and
numbering (#2 "Benchmark harness" is now milestone 3, and there is no issue for
the frontend milestone). They should be retitled before milestone 2 starts.

**Next:** Milestone 2, frontend foundation. See `PLAN.md`. The UI framework is
chosen there.
