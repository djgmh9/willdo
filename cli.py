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

    def _show_tasks(self) -> None:
        tasks = self.engine.list_tasks()
        print("\nTasks")
        if not tasks:
            print("  No tasks yet. Use 'a' to add one.")
        for task in tasks:
            status = "x" if task.is_completed else " "
            print(f"  {task.id}. [{status}] {task.title}")

    def _read_id(self) -> int:
        try:
            return int(input("Task ID: ").strip())
        except ValueError:
            raise ValueError("Enter a positive integer task ID.") from None

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
                self._show_tasks()
                print("\n[a] Add  [e] Edit  [d] Delete  [c] Complete  [q] Quit")
                command = input("> ").strip().lower()
                try:
                    if command in {"q", "quit"}:
                        break
                    if command in {"a", "add"}:
                        title = input("Title: ")
                        self._change(lambda engine: engine.add_task(title))
                    elif command in {"e", "edit"}:
                        task_id = self._read_id()
                        self.engine.get_task(task_id)
                        title = input("New title: ")
                        self._change(lambda engine: engine.edit_task(task_id, title))
                    elif command in {"d", "delete"}:
                        task_id = self._read_id()
                        self._change(lambda engine: engine.delete_task(task_id))
                    elif command in {"c", "complete"}:
                        task_id = self._read_id()
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
