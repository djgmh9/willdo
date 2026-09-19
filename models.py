"""Immutable domain objects shared by the application layers."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    id: int
    title: str
    is_completed: bool = False

    def __post_init__(self) -> None:
        if type(self.id) is not int or self.id <= 0:
            raise ValueError("Task ID must be a positive integer.")
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("Task title must be a non-empty string.")
        if type(self.is_completed) is not bool:
            raise ValueError("Task completion status must be a boolean.")
        object.__setattr__(self, "title", self.title.strip())
