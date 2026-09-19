"""JSON persistence, independent of the business logic and console UI."""

import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Protocol

from models import Task


class StorageError(Exception):
    """A readable persistence error suitable for displaying in the UI."""


class TaskStorage(Protocol):
    def load(self) -> list[Task]: ...

    def save(self, tasks: list[Task]) -> None: ...


class JsonStorage:
    def __init__(self, path: str | Path = "tasks.json") -> None:
        self.path = Path(path)

    def load(self) -> list[Task]:
        """Missing files start empty; invalid files are never silently reset."""
        try:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError:
            return []
        except (json.JSONDecodeError, UnicodeError) as exc:
            raise StorageError(f"Invalid JSON in {self.path}: {exc}") from exc
        except OSError as exc:
            raise StorageError(f"Cannot read {self.path}: {exc}") from exc

        try:
            if not isinstance(data, list):
                raise ValueError("Expected a JSON array of tasks.")
            tasks = []
            seen_ids: set[int] = set()
            for item in data:
                if not isinstance(item, dict) or set(item) != {
                    "id", "title", "is_completed"
                }:
                    raise ValueError("Each task needs id, title, and is_completed.")
                task = Task(**item)
                if task.id in seen_ids:
                    raise ValueError(f"Duplicate task ID: {task.id}.")
                seen_ids.add(task.id)
                tasks.append(task)
            return tasks
        except (TypeError, ValueError) as exc:
            raise StorageError(f"Invalid task data in {self.path}: {exc}") from exc

    def save(self, tasks: list[Task]) -> None:
        """Replace the file atomically, keeping the old file if writing fails."""
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent,
                prefix=f".{self.path.name}.", suffix=".tmp", delete=False,
            ) as file:
                temporary_path = Path(file.name)
                json.dump([asdict(task) for task in tasks], file, indent=2,
                          ensure_ascii=False)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, self.path)
        except (OSError, UnicodeError, TypeError, ValueError) as exc:
            raise StorageError(f"Cannot save {self.path}: {exc}") from exc
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass  # Cleanup must not obscure the original write error.
