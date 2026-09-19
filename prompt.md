Act as an expert Software Engineer helping me build a clean, production-grade To-Do List CLI application in Python for a time-constrained take-home assessment. 

I have already defined the scope and architectural direction before prompting:
- Target & MVP: A lightweight, keyboard-friendly CLI app focused purely on the minimum features (Add, edit, delete tasks, mark complete).
- Persistence: A local JSON file ('tasks.json') that auto-saves state.
- Architecture: A highly decoupled design separating UI, Logic, and Storage to ensure strict unit-testability (inspired by clean architecture / OOP layering).

Please generate the complete, working codebase divided into these specific files:

1. `storage.py` - Handles reading/writing data to JSON. Must include basic error handling for corrupt or missing files.
2. `models.py` - Contains the Task class/data structure (id, title, is_completed).
3. `engine.py` - Contains the core business logic (CRUD operations). This file must be entirely pure logic with NO print() or input() statements so it can be perfectly unit tested.
4. `cli.py` - Handles user interaction, menus, and printing to the console.
5. `main.py` - Entry point to initialize and boot the application.

Also, provide a comprehensive unit test suite (`test_todo.py`) using Python's built-in `unittest` module that covers the core logic in `engine.py`. Let's build the code now.
