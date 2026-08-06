# Build plan

Seven milestones. Each is one issue, one or more commits, and an entry appended
to `PROGRESS.md`.

The benchmark comes first — milestones 1 and 2, before the server does anything
interesting. Everything this project claims is a before-and-after, so the thing
that produces the before has to exist before there is anything to change.

## 1 — Server and tool surface

- MCP server over the official Python SDK, stdio transport
- The seven codebase-intelligence tools, working, against a real Git repository
- Deliberately naive first-draft descriptions and loose schemas — this is the
  starting point the optimizer has to improve on, and making it artificially
  good would hide the effect

**Done when:** the server connects from an MCP client and all seven tools return
correct results against this repository.

## 2 — Benchmark harness

- Task suite: a natural-language request plus the tool call sequence that
  correctly serves it
- Development / held-out split, enforced in code rather than by discipline
- Scorer: tool-selection accuracy, argument validity, chain length, token cost
- Baseline run recorded against the milestone-1 surface

**Done when:** the baseline number is recorded in `PROGRESS.md`. It should be
unimpressive; a strong baseline means the tasks are too easy.

## 3 — Telemetry

- Structured log of every tool call: tool, arguments, outcome, error class,
  latency, position in chain
- Failure taxonomy: wrong tool selected, malformed arguments, right tool with
  wrong arguments, right call with an empty result
- Aggregation queries over the log

**Done when:** a benchmark run produces a telemetry log that identifies which
specific tools are being misused and how.

## 4 — Description rewriting

- Propose rewrites from telemetry failure patterns
- Re-benchmark each candidate on the development split
- Accept only on improvement; record every rejection and why
- Version history for each description, so a regression can be traced

**Done when:** development-split accuracy improves and every accepted rewrite
has a recorded before/after number attached.

## 5 — Schema tightening

- Detect parameter-level failure patterns from telemetry
- Propose constraints: enums, formats, required fields, bounded ranges
- Validate that no previously-valid call becomes invalid — a tightening that
  breaks working calls is a regression even if accuracy rises

**Done when:** argument-validity error rate drops measurably, with no loss in
task coverage.

## 6 — Macro synthesis

- Mine telemetry for recurring call chains
- Propose composite tools for the frequent ones
- Measure the tradeoff honestly: a macro reduces round trips but adds another
  tool to choose among, and past some count that hurts selection accuracy

**Done when:** chain length and token cost per task both drop, and the point
where adding macros starts to hurt selection is identified.

## 7 — Results

- Full optimization run, then evaluation on the held-out split
- `docs/results.md`: baseline versus optimized on held-out tasks, per-strategy
  ablations, and an honest account of what did not work
- README quickstart

**Done when:** the held-out number is published with the development number
beside it. A large gap between them is itself the finding and gets reported
rather than buried.
