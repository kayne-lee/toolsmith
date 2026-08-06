import pytest

from toolsmith.bench.split import HeldOutAccessError, Split, Task, select


def make_tasks(n: int = 200) -> list[Task]:
    return [Task(task_id=f"t{i}", request=f"request {i}", expected_tools=("read_file",))
            for i in range(n)]


def test_split_assignment_is_deterministic() -> None:
    a = Task(task_id="t1", request="x", expected_tools=())
    b = Task(task_id="t1", request="totally different", expected_tools=("read_file",))
    assert a.split is b.split


def test_both_splits_are_populated() -> None:
    tasks = make_tasks()
    dev = select(tasks, Split.DEVELOPMENT)
    held = select(tasks, Split.HELD_OUT, publishing=True)
    assert len(dev) > 0
    assert len(held) > 0
    assert len(dev) + len(held) == len(tasks)


def test_splits_are_disjoint() -> None:
    tasks = make_tasks()
    dev = {t.task_id for t in select(tasks, Split.DEVELOPMENT)}
    held = {t.task_id for t in select(tasks, Split.HELD_OUT, publishing=True)}
    assert dev.isdisjoint(held)


def test_held_out_requires_declaring_intent() -> None:
    with pytest.raises(HeldOutAccessError, match="published results only"):
        select(make_tasks(), Split.HELD_OUT)


def test_development_needs_no_declaration() -> None:
    assert select(make_tasks(), Split.DEVELOPMENT)
