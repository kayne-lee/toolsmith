"""Development / held-out split, enforced rather than trusted.

The single most likely way this project produces a meaningless result is by
optimizing against the tasks it later reports numbers on. Discipline is not
sufficient protection — three sessions from now nobody will remember which
split a convenience function was reading.

So the split is a type. Optimization code accepts only `Split.DEVELOPMENT`, and
asking for held-out tasks requires saying `publishing=True` out loud at the call
site, where it is visible in review and in the diff.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum


class Split(Enum):
    DEVELOPMENT = "development"
    HELD_OUT = "held_out"


class HeldOutAccessError(RuntimeError):
    """Raised when held-out tasks are requested without declaring intent."""


@dataclass(frozen=True, slots=True)
class Task:
    """One benchmark task: a request, and the tool calls that correctly serve it."""

    task_id: str
    request: str
    expected_tools: tuple[str, ...]

    @property
    def split(self) -> Split:
        """Deterministic assignment from the task ID.

        Hash-based rather than stored, so a task cannot drift between splits
        when the suite is edited, and a new task's split is not a choice anyone
        makes by hand.
        """
        digest = hashlib.sha256(self.task_id.encode()).digest()
        return Split.HELD_OUT if digest[0] % 4 == 0 else Split.DEVELOPMENT


def select(tasks: list[Task], split: Split, *, publishing: bool = False) -> list[Task]:
    """Filter tasks to one split.

    Requesting HELD_OUT requires `publishing=True`. This is not security — it is
    a speed bump placed exactly where the mistake would otherwise be silent.
    """
    if split is Split.HELD_OUT and not publishing:
        raise HeldOutAccessError(
            "Held-out tasks are for published results only. Optimization and "
            "iteration use Split.DEVELOPMENT. If you are generating the numbers "
            "for docs/results.md, pass publishing=True."
        )
    return [task for task in tasks if task.split is split]
