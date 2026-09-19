"""Console interaction and coordination of domain changes with persistence."""

from collections.abc import Callable
from copy import deepcopy

from engine import TaskNotFoundError, TodoEngine
from models import Task
from storage import StorageError, TaskStorage


class TodoCLI:
    def __init__(self, engine: TodoEngine, storage: TaskStorage) -> None:
        self.engine = engine
        self.storage = storage

    def _show_tasks(self) -> list[Task]:
        tasks = self.engine.list_tasks()
        print("\nTasks")
        if not tasks:
            print("  No tasks yet. Use 'a' to add one.")
        for number, task in enumerate(tasks, start=1):
            status = "x" if task.is_completed else " "
            print(f"  {number}. [{status}] {task.title}")
        return tasks

    def _read_task_id(self, displayed_tasks: list[Task], selection: str | None) -> int:
        """Resolve a display number using the exact list shown for this command."""
        if selection is None:
            selection = input("Task number: ").strip()
        try:
            number = int(selection)
        except ValueError:
            raise ValueError("Enter a positive integer task number.") from None
        if not displayed_tasks:
            raise ValueError("There are no tasks to select.")
        if not 1 <= number <= len(displayed_tasks):
            raise ValueError(f"Choose a task number from 1 to {len(displayed_tasks)}.")
        return displayed_tasks[number - 1].id

    def _change(self, operation: Callable[[TodoEngine], Task]) -> None:
        # Only publish the new in-memory state after persistence succeeds.
        candidate = deepcopy(self.engine)
        operation(candidate)
        self.storage.save(candidate.list_tasks())
        self.engine = candidate
        print("Saved.")

    def run(self) -> None:
        print("To-Do List")
        try:
            while True:
                displayed_tasks = self._show_tasks()
                print("\n[a] Add  [e] Edit  [d] Delete  [c] Complete  [q] Quit")
                print("Use the displayed task number (for example: delete 1).")
                parts = input("> ").strip().split(maxsplit=1)
                command = parts[0].lower() if parts else ""
                selection = parts[1] if len(parts) > 1 else None
                try:
                    if selection is not None and command not in {
                        "e", "edit", "d", "delete", "c", "complete"
                    }:
                        raise ValueError("Only edit, delete, and complete accept a task number.")
                    if command in {"q", "quit"}:
                        break
                    if command in {"a", "add"}:
                        title = input("Title: ")
                        self._change(lambda engine: engine.add_task(title))
                    elif command in {"e", "edit"}:
                        task_id = self._read_task_id(displayed_tasks, selection)
                        title = input("New title: ")
                        self._change(lambda engine: engine.edit_task(task_id, title))
                    elif command in {"d", "delete"}:
                        task_id = self._read_task_id(displayed_tasks, selection)
                        self._change(lambda engine: engine.delete_task(task_id))
                    elif command in {"c", "complete"}:
                        task_id = self._read_task_id(displayed_tasks, selection)
                        self._change(lambda engine: engine.mark_complete(task_id))
                    else:
                        print("Unknown command. Choose a, e, d, c, or q.")
                except (ValueError, TaskNotFoundError) as exc:
                    print(f"Error: {exc}")
                except StorageError as exc:
                    print(f"Error: {exc}\nChange was not applied. Try again.")
        except (EOFError, KeyboardInterrupt):
            print()
        print("Goodbye.")
