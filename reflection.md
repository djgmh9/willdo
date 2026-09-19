# Project Reflection

## 1. How did you break down the problem before prompting?

Before prompting, I used software engineering principles inspired by NUS CS2103T to define the MVP: adding, editing, deleting, and completing tasks, with automatic JSON persistence.

I separated responsibilities into user interaction (`cli.py`), business logic (`engine.py`), data modeling (`models.py`), storage (`storage.py`), and initialization (`main.py`). I required the engine to contain no console I/O so it could be tested independently.

A Python CLI with JSON kept setup simple and the scope manageable within the 2–3 hour assessment window. I requested tests using Python's built-in `unittest` module to avoid third-party dependencies.

## 2. What did the AI get wrong, and how did you fix it?

The initial implementation displayed internal task IDs. Deleting task 1 left tasks numbered 2 and 3. Selection still worked, but the numbers no longer matched positions in the list, making interaction less intuitive.

I identified this usability issue and proposed separating internal IDs from display numbers. The AI updated `cli.py` to enumerate tasks sequentially and map selections back to their internal IDs. Now, `delete 1` targets the first visible task; editing and completing use the same mapping.

The AI also added regression tests. My contribution was identifying the problem and specifying the behavior. JSON error handling and duplicate-ID validation were already present in the original implementation.

## 3. What did you deliberately not delegate to AI, and why?

I retained control over scope, architecture, and usability decisions because these defined what a successful solution should achieve. I delegated implementation and automated test generation, including edge cases, to AI.

I also performed independent manual checks: entering mixed-case commands such as `DeLete 4` and injecting duplicate task IDs into `tasks.json`. These checks helped verify the generated input normalization and validation against actual application behavior. The AI implemented those safeguards; my role was independently checking them rather than assuming generated code was correct.

## 4. What would you do differently with more time?

I would evaluate SQLite and explicitly design and test concurrent updates and recovery. The current JSON implementation already saves atomically, but assumes one running process per file.

I would explore a terminal UI with keyboard navigation and scrollable lists, preserving the independent engine and storage layers. Creation and completion timestamps could support history and productivity summaries; deadline filtering would require a separate due-date field.

Finally, I would automate the mixed-case and whitespace checks and document a repeatable manual walkthrough of normal workflows and recovery scenarios.
