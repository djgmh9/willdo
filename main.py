"""Application composition and entry point: python main.py."""

import sys

from cli import TodoCLI
from engine import TodoEngine
from storage import JsonStorage, StorageError


def main() -> int:
    storage = JsonStorage("tasks.json")
    try:
        engine = TodoEngine(storage.load())
    except StorageError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print("Repair or move tasks.json before restarting. The file was not changed.",
              file=sys.stderr)
        return 1
    TodoCLI(engine, storage).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
