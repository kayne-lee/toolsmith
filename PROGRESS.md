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
