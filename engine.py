"""In-memory task operations. This module performs no I/O."""

from collections.abc import Iterable
from dataclasses import replace

from models import Task


class TaskNotFoundError(LookupError):
    """Raised when an operation references an unknown task ID."""


class TodoEngine:
    def __init__(self, tasks: Iterable[Task] = ()) -> None:
        self._tasks: dict[int, Task] = {}
        for task in tasks:
            if not isinstance(task, Task):
                raise ValueError("Initial tasks must be Task objects.")
            if task.id in self._tasks:
                raise ValueError(f"Duplicate task ID: {task.id}.")
            self._tasks[task.id] = task
        self._next_id = max(self._tasks, default=0) + 1

    def list_tasks(self) -> list[Task]:
        """Return an independent list of immutable tasks, ordered by ID."""
        return sorted(self._tasks.values(), key=lambda task: task.id)

    def get_task(self, task_id: int) -> Task:
        if type(task_id) is not int or task_id <= 0:
            raise ValueError("Task ID must be a positive integer.")
        try:
            return self._tasks[task_id]
        except KeyError:
            raise TaskNotFoundError(f"Task {task_id} was not found.") from None

    def add_task(self, title: str) -> Task:
        task = Task(id=self._next_id, title=title)
        self._tasks[task.id] = task
        self._next_id += 1
        return task

    def edit_task(self, task_id: int, title: str) -> Task:
        task = replace(self.get_task(task_id), title=title)
        self._tasks[task_id] = task
        return task

    def delete_task(self, task_id: int) -> Task:
        task = self.get_task(task_id)
        del self._tasks[task_id]
        return task

    def mark_complete(self, task_id: int) -> Task:
        """Complete a task; completing it again is harmless."""
        task = replace(self.get_task(task_id), is_completed=True)
        self._tasks[task_id] = task
        return task
