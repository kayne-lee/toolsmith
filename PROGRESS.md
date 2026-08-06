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
