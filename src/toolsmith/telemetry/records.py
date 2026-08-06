"""Telemetry records — the raw material every optimization strategy reads from.

The failure taxonomy is the important part. "The call failed" is not actionable;
each of these failure modes points at a different fix:

- WRONG_TOOL      → the description overclaims or a rival's underclaims
- MALFORMED_ARGS  → the schema is too permissive
- BAD_ARGS        → the parameter description is ambiguous
- EMPTY_RESULT    → right call, wrong expectation set by the description
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class Outcome(Enum):
    SUCCESS = "success"
    WRONG_TOOL = "wrong_tool"
    MALFORMED_ARGS = "malformed_args"
    BAD_ARGS = "bad_args"
    EMPTY_RESULT = "empty_result"
    ERROR = "error"

    @property
    def is_failure(self) -> bool:
        return self is not Outcome.SUCCESS


@dataclass(frozen=True, slots=True)
class CallRecord:
    """One tool invocation, with enough context to diagnose why it went wrong.

    `chain_position` and `chain_id` matter for macro synthesis: a recurring
    sequence is only detectable if calls know which sequence they belonged to.
    """

    tool_name: str
    arguments: dict[str, Any]
    outcome: Outcome
    chain_id: str
    chain_position: int
    latency_ms: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    error_detail: str | None = None
    task_id: str | None = None

    def __post_init__(self) -> None:
        if self.chain_position < 0:
            raise ValueError("chain_position must be non-negative")
        if self.outcome is Outcome.SUCCESS and self.error_detail is not None:
            raise ValueError("a successful call cannot carry an error detail")
