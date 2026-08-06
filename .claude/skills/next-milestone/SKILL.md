---
name: next-milestone
description: Pick up this repository's work where the last session stopped and advance the next milestone. Use when the user says "continue", "next milestone", "keep going", or asks what state the project is in.
---

# Next milestone

Sessions on this repository start with no memory of the previous one.
`PROGRESS.md` is the handoff.

## Procedure

1. **Read `PROGRESS.md` bottom-up.** The last entry is where work stopped. Read
   at least the last two — the second-to-last often explains a decision the last
   one depends on. Benchmark numbers live here; find the most recent one and the
   split it came from before changing anything.
2. **Read `PLAN.md`** for the milestone about to be worked. The plan is fixed; if
   its scope turns out to be wrong, say so and propose an amendment rather than
   silently doing something else.
3. **Confirm the working tree is clean** (`git status`). Uncommitted changes mean
   a previous session ended mid-work — read the diff before doing anything.
4. **Do the work.** Tests are written alongside the code, not deferred. A
   milestone is not done because the code exists; it is done when its
   "Done when" criterion in `PLAN.md` is demonstrably met.
5. **Run the full check** before committing:
   ```bash
   uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
   ```
   All four must pass. If something fails and cannot be fixed within scope, stop
   and record the failure in `PROGRESS.md` rather than committing over it.
6. **Commit.** Small, focused commits with imperative subjects
   (`add schema tightening proposer`, not `Added schema tightening proposer`).
   **Never add a `Co-Authored-By` trailer or any AI-attribution footer.**
7. **Append to `PROGRESS.md`**: what was built, what was decided and why, the
   benchmark numbers with their split, what is blocked, and what the next
   session should start on.
8. **Close the milestone's issue** with a comment summarizing the outcome.

## Rules specific to this repository

- **Never touch the held-out split except to publish.** `Split.HELD_OUT`
  requires `publishing=True` for exactly this reason. If you find yourself
  wanting to peek at held-out performance mid-iteration, that is the failure
  this project exists to avoid — don't.
- **Every accepted optimization has a recorded before/after.** A rewritten
  description that was not benchmarked is not an improvement, it is a change.
  Record rejections too, with the number that caused them; the rejections are
  half the finding.
- **Report regressions in the first sentence.** If an optimization strategy did
  not work, `docs/results.md` says so plainly. "This approach did not improve
  selection accuracy" is a legitimate result and a more credible repository than
  one where everything worked.
- **Do not generate or register executable tool code.** Descriptions, schemas,
  and composition of existing implementations only. If a milestone seems to call
  for code generation, it does not — re-read `PLAN.md`.
- **Watch the tool-count tradeoff on macro synthesis.** Each macro removes round
  trips and adds a candidate to choose among. Past some count, selection accuracy
  falls. Find that point and document it rather than assuming more is better.
- **API calls use `claude-opus-5` with adaptive thinking.** Cache the stable
  instruction prefix — the optimizer re-runs the same prompt shape many times per
  round and this is the dominant cost.
