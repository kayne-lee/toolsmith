# Build plan

Eight milestones. Each is one issue, one or more commits, and an entry appended
to `PROGRESS.md`.

**The product is the optimizer and its benchmark, not the server.** They must
work against any MCP server, which toolsmith neither wrote nor can edit. The
codebase-intelligence server from milestone 1 is the *reference target*: a
server under our control, with deliberately ambiguous tools, to develop and test
against. Nothing outside milestone 1 may depend on its internals. It is reached
only through the MCP protocol, as any third-party server would be.

The mechanism that makes this possible is a **proxy**: an MCP server that sits
between the client and the target server, passes calls through, records them,
and serves the target's tools with optimized descriptions and schemas laid over
the originals. The target is never modified.

**The frontend comes second and grows with the project.** Milestone 2 builds it
with the first two views; every milestone after that adds the view for what it
produces, and is not done until that view works. So development can be watched
as it happens, not only once it is finished. Everything a milestone produces is
written as a structured record under `runs/`, and the frontend only reads those
records, so anything it shows can be reproduced from them.

The benchmark comes before any optimization. Everything this project claims is a
before-and-after, so the thing that produces the before has to exist before
there is anything to change.

## 1 — Reference target server

- MCP server over the official Python SDK, stdio transport
- The seven codebase-intelligence tools, working, against a real Git repository
- Deliberately naive first-draft descriptions and loose schemas — this is the
  starting point the optimizer has to improve on, and making it artificially
  good would hide the effect
- Kept separate from the optimizer packages: it is a test subject, and the
  optimizer must not import from it

**Done when:** the server connects from an MCP client and all seven tools return
correct results against this repository.

## 2 — Frontend foundation

A local web UI, started with `toolsmith ui`. Read-only: it changes nothing.

- The `runs/` record format, versioned, since the frontend and every later
  milestone read and write it
- **Project view:** the milestones from `PLAN.md` with their status, the
  `PROGRESS.md` log, and every benchmark number recorded so far with its split.
  This is the view for watching development
- **Tool surface view:** a target's tools as `tools/list` reports them, read
  over MCP: each tool's description and input schema, and how they changed
  across versions once later milestones start changing them
- UI framework chosen here, and the choice recorded in `PROGRESS.md`

**Done when:** `toolsmith ui` shows the project's current state and the
reference target's seven tools, read live from the running server.

## 3 — Benchmark harness

- Runs against any MCP server, given its launch command: connects as an MCP
  client, reads `tools/list`, and has a model attempt each task with those tools
- Task suite: a natural-language request plus the tool call sequence that
  correctly serves it. Suites belong to a target server; the reference target's
  suite is the first one
- Development / held-out split, enforced in code rather than by discipline
- Scorer: tool-selection accuracy, argument validity, chain length, token cost
- Each run writes a run record to `runs/`: target, tool surface version, split,
  per-task results, and scores
- Baseline run recorded against the milestone-1 surface
- **Runs view:** every benchmark run per target and split, with its four scores
  over time
- **Tool confusion view:** a matrix of the tool each task needed against the
  tool the model picked. This is where overlapping tools show up, so it is the
  main view of the project

**Done when:** the baseline number is recorded in `PROGRESS.md` and shows in the
runs and confusion views. It should be unimpressive; a strong baseline means the
tasks are too easy.

## 4 — Proxy and telemetry

- MCP proxy: launches or connects to a target server, re-exposes its tools, and
  forwards every call unchanged
- Override layer in the proxy: per-tool description and schema overrides, empty
  for now, which milestones 5–6 fill
- Structured log of every tool call: tool, arguments, outcome, error class,
  latency, position in chain
- Failure taxonomy: wrong tool selected, malformed arguments, right tool with
  wrong arguments, right call with an empty result
- Aggregation queries over the log
- Telemetry stored with the run record of the benchmark run that produced it
- **Failures view:** the failure taxonomy broken down per tool, with example
  calls

**Done when:** a benchmark run through the proxy, against the reference target,
produces a telemetry log that identifies which specific tools are being misused
and how, visible in the failures view — and the proxy is shown to pass calls
through without changing results.

## 5 — Description rewriting

- Propose rewrites from telemetry failure patterns
- Re-benchmark each candidate on the development split
- Accept only on improvement; record every rejection and why
- Version history for each description, so a regression can be traced
- Output is a set of overrides the proxy serves, never an edit to the target
- Every candidate, accepted or rejected, written to `runs/` with its diff and
  its development-split numbers
- **Optimization history view:** each proposed rewrite as a diff against the
  original, with before/after numbers and why it was accepted or rejected

**Done when:** development-split accuracy improves, every accepted rewrite has a
recorded before/after number attached, and both show in the history view.

## 6 — Schema tightening

- Detect parameter-level failure patterns from telemetry
- Propose constraints: enums, formats, required fields, bounded ranges
- Validate that no previously-valid call becomes invalid — a tightening that
  breaks working calls is a regression even if accuracy rises
- Schema candidates added to the optimization history view as schema diffs

**Done when:** argument-validity error rate drops measurably, with no loss in
task coverage, and each tightening shows in the history view.

## 7 — Macro synthesis

- Mine telemetry for recurring call chains
- Propose composite tools for the frequent ones, served by the proxy as a fixed
  sequence of calls to the target's existing tools
- Measure the tradeoff honestly: a macro reduces round trips but adds another
  tool to choose among, and past some count that hurts selection accuracy
- **Macro tradeoff view:** number of macros against selection accuracy and chain
  length, marking the point where more macros start to hurt

**Done when:** chain length and token cost per task both drop, and the point
where adding macros starts to hurt selection is identified and shown in the
tradeoff view.

## 8 — Results

- Full optimization run, then evaluation on the held-out split
- A second, third-party MCP server as a target, with its own task suite, to
  show the optimizer is not tuned to the reference target
- `docs/results.md`: baseline versus optimized on held-out tasks, per-strategy
  ablations, and an honest account of what did not work
- **Held-out results view**, populated only from the published run. Before
  publishing, the frontend shows no held-out number anywhere, the same guard the
  split has in code
- README quickstart, including screenshots of the frontend

**Done when:** the held-out number is published with the development number
beside it, in `docs/results.md` and the frontend. A large gap between them is
itself the finding and gets reported rather than buried.
