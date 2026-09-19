# To-Do List CLI

A dependency-free Python 3.10+ application for adding, editing, deleting, and
completing tasks.

```sh
python main.py
python -m unittest -v
```

Use `a`, `e`, `d`, `c`, and `q` (or their full command names). Tasks are listed
after each command. Each successful change automatically saves to `tasks.json`
in the current working directory. EOF and Ctrl+C exit cleanly.

## Design

- `models.py`: validated, immutable task values.
- `engine.py`: in-memory CRUD and ID allocation, with no console or filesystem I/O.
- `storage.py`: JSON validation and atomic file replacement.
- `cli.py`: keyboard interaction and coordination of changes with saving.
- `main.py`: constructs the dependencies and starts the application.

The CLI applies each change to a copy of the engine and adopts it only after
saving succeeds. Failed saves therefore leave the current session unchanged.
Missing data files start an empty list. Corrupt JSON or invalid task data stops
startup with an actionable error and preserves the original file.

IDs are positive integers allocated above the highest initial ID, increasing
throughout a session. Deleted IDs may be reused after restarting. This application
supports one running process per data file; concurrent writers are outside scope.

`test_todo.py` uses the standard-library `unittest` module. Engine tests need no
filesystem or UI. Additional tests cover persistence and CLI save failures.
