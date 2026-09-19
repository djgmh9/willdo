"""Run with: python -m unittest -v."""

import io
import json
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import Mock, patch

from cli import TodoCLI
from engine import TaskNotFoundError, TodoEngine
from main import main
from models import Task
from storage import JsonStorage, StorageError, TaskStorage


class TodoEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = TodoEngine()

    def test_new_engine_is_empty(self) -> None:
        self.assertEqual(self.engine.list_tasks(), [])

    def test_add_normalizes_title_and_defaults_to_incomplete(self) -> None:
        task = self.engine.add_task("  Buy milk  ")
        self.assertEqual(task, Task(1, "Buy milk", False))
        self.assertEqual(self.engine.get_task(1), task)

    def test_add_assigns_unique_increasing_ids(self) -> None:
        tasks = [self.engine.add_task("Same title") for _ in range(3)]
        self.assertEqual([task.id for task in tasks], [1, 2, 3])

    def test_add_rejects_invalid_titles_without_consuming_id(self) -> None:
        for title in ("", " ", "\t\n", None, 123, False):
            with self.subTest(title=title), self.assertRaises(ValueError):
                self.engine.add_task(title)
        self.assertEqual(self.engine.list_tasks(), [])
        self.assertEqual(self.engine.add_task("Valid").id, 1)

    def test_unicode_title(self) -> None:
        self.assertEqual(self.engine.add_task("买牛奶 🥛").title, "买牛奶 🥛")

    def test_restores_tasks_in_id_order_and_allocates_above_maximum(self) -> None:
        tasks = [Task(10, "Later", True), Task(3, "Earlier")]
        engine = TodoEngine(iter(tasks))
        self.assertEqual(engine.list_tasks(), [tasks[1], tasks[0]])
        self.assertEqual(engine.add_task("Next").id, 11)

    def test_initial_collection_is_not_retained(self) -> None:
        tasks = [Task(1, "Keep")]
        engine = TodoEngine(tasks)
        tasks.clear()
        self.assertEqual(engine.list_tasks(), [Task(1, "Keep")])

    def test_duplicate_initial_ids_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            TodoEngine([Task(1, "One"), Task(1, "Two")])

    def test_invalid_initial_object_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            TodoEngine([{"id": 1, "title": "Invalid"}])

    def test_list_is_an_independent_snapshot(self) -> None:
        task = self.engine.add_task("Keep")
        snapshot = self.engine.list_tasks()
        snapshot.clear()
        self.assertEqual(self.engine.list_tasks(), [task])

    def test_tasks_cannot_be_mutated_outside_engine(self) -> None:
        task = self.engine.add_task("Keep")
        with self.assertRaises(FrozenInstanceError):
            task.title = "Bypassed validation"

    def test_edit_preserves_id_and_completion(self) -> None:
        original = self.engine.add_task("Old")
        self.engine.mark_complete(original.id)
        edited = self.engine.edit_task(original.id, "  New  ")
        self.assertEqual(edited, Task(original.id, "New", True))
        self.assertEqual(self.engine.get_task(original.id), edited)
        self.assertEqual(original.title, "Old")

    def test_invalid_edit_leaves_task_unchanged(self) -> None:
        task = self.engine.add_task("Keep")
        for title in ("", "  ", None, 3):
            with self.subTest(title=title), self.assertRaises(ValueError):
                self.engine.edit_task(task.id, title)
            self.assertEqual(self.engine.get_task(task.id), task)

    def test_delete_returns_task_and_preserves_other_tasks(self) -> None:
        removed = self.engine.add_task("Remove")
        kept = self.engine.add_task("Keep")
        self.assertEqual(self.engine.delete_task(removed.id), removed)
        self.assertEqual(self.engine.list_tasks(), [kept])
        with self.assertRaises(TaskNotFoundError):
            self.engine.get_task(removed.id)

    def test_deleted_highest_id_is_not_reused_during_session(self) -> None:
        task = self.engine.add_task("Remove")
        self.engine.delete_task(task.id)
        self.assertEqual(self.engine.add_task("Next").id, 2)

    def test_completion_is_idempotent_and_preserves_title(self) -> None:
        task = self.engine.add_task("Finish")
        expected = Task(task.id, task.title, True)
        self.assertEqual(self.engine.mark_complete(task.id), expected)
        self.assertEqual(self.engine.mark_complete(task.id), expected)
        self.assertEqual(self.engine.list_tasks(), [expected])

    def test_operations_do_not_change_unrelated_tasks(self) -> None:
        first = self.engine.add_task("First")
        second = self.engine.add_task("Second")
        self.engine.edit_task(first.id, "Updated")
        self.engine.mark_complete(first.id)
        self.assertEqual(self.engine.get_task(second.id), second)

    def test_unknown_ids_fail_without_mutation(self) -> None:
        task = self.engine.add_task("Keep")
        operations = (
            self.engine.get_task,
            lambda task_id: self.engine.edit_task(task_id, "New"),
            self.engine.delete_task,
            self.engine.mark_complete,
        )
        for operation in operations:
            with self.subTest(operation=operation), self.assertRaises(TaskNotFoundError):
                operation(99)
            self.assertEqual(self.engine.list_tasks(), [task])

    def test_invalid_ids_fail_without_mutation(self) -> None:
        task = self.engine.add_task("Keep")
        operations = (
            self.engine.get_task,
            lambda task_id: self.engine.edit_task(task_id, "New"),
            self.engine.delete_task,
            self.engine.mark_complete,
        )
        for operation in operations:
            for task_id in (0, -1, True, False, 1.0, "1", None):
                with self.subTest(operation=operation, task_id=task_id):
                    with self.assertRaises(ValueError):
                        operation(task_id)
                    self.assertEqual(self.engine.list_tasks(), [task])

    def test_engines_do_not_share_state(self) -> None:
        self.engine.add_task("Private")
        self.assertEqual(TodoEngine().list_tasks(), [])


class JsonStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "tasks.json"
        self.storage = JsonStorage(self.path)

    def test_missing_file_loads_empty_without_creating_file(self) -> None:
        self.assertEqual(self.storage.load(), [])
        self.assertFalse(self.path.exists())

    def test_round_trip_preserves_all_fields_and_unicode(self) -> None:
        tasks = [Task(2, "买牛奶 🥛"), Task(7, "Done", True)]
        self.storage.save(tasks)
        self.assertEqual(JsonStorage(self.path).load(), tasks)
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(data[1], {"id": 7, "title": "Done", "is_completed": True})
        self.storage.save([])
        self.assertEqual(self.storage.load(), [])

    def test_corrupt_json_is_reported_and_preserved(self) -> None:
        for content in ("", "{broken", "[{]"):
            with self.subTest(content=content):
                self.path.write_text(content, encoding="utf-8")
                with self.assertRaises(StorageError):
                    self.storage.load()
                self.assertEqual(self.path.read_text(encoding="utf-8"), content)

    def test_invalid_encoding_is_reported(self) -> None:
        self.path.write_bytes(b"\xff\xfe")
        with self.assertRaises(StorageError):
            self.storage.load()

    def test_invalid_task_data_is_rejected(self) -> None:
        valid = {"id": 1, "title": "Task", "is_completed": False}
        invalid_payloads = [
            {}, None, [None], [{"id": 1, "title": "Missing status"}],
            [{**valid, "extra": 1}], [valid, valid],
            [{**valid, "id": True}], [{**valid, "id": 0}],
            [{**valid, "id": "1"}], [{**valid, "title": " "}],
            [{**valid, "title": 12}], [{**valid, "is_completed": "false"}],
            [{**valid, "is_completed": 1}],
        ]
        for data in invalid_payloads:
            with self.subTest(data=data):
                self.path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(StorageError):
                    self.storage.load()

    def test_read_permission_error_is_wrapped(self) -> None:
        with patch.object(Path, "open", side_effect=PermissionError("Denied")):
            with self.assertRaises(StorageError):
                self.storage.load()

    def test_failed_replace_preserves_file_and_cleans_up_temp_file(self) -> None:
        self.storage.save([Task(1, "Original")])
        original = self.path.read_bytes()
        with patch("storage.os.replace", side_effect=OSError("Disk failure")):
            with self.assertRaises(StorageError):
                self.storage.save([Task(2, "Replacement")])
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_failed_write_preserves_file_and_cleans_up_temp_file(self) -> None:
        self.storage.save([Task(1, "Original")])
        original = self.path.read_bytes()
        with patch("storage.json.dump", side_effect=OSError("Disk full")):
            with self.assertRaises(StorageError):
                self.storage.save([Task(2, "Replacement")])
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])


class CLITests(unittest.TestCase):
    def run_cli(self, cli: TodoCLI, commands: list[str]) -> str:
        output = io.StringIO()
        with patch("builtins.input", side_effect=commands), patch("sys.stdout", output):
            cli.run()
        return output.getvalue()

    def test_full_workflow_autosaves_each_change(self) -> None:
        storage = Mock(spec=TaskStorage)
        cli = TodoCLI(TodoEngine(), storage)
        self.run_cli(cli, ["a", "First", "e", "1", "Updated", "c", "1", "d", "1", "q"])
        self.assertEqual(cli.engine.list_tasks(), [])
        self.assertEqual([call.args[0] for call in storage.save.call_args_list], [
            [Task(1, "First")], [Task(1, "Updated")],
            [Task(1, "Updated", True)], [],
        ])

    def test_failed_save_does_not_apply_change_and_allows_retry(self) -> None:
        storage = Mock(spec=TaskStorage)
        storage.save.side_effect = [StorageError("Disk full"), None]
        cli = TodoCLI(TodoEngine(), storage)
        output = self.run_cli(cli, ["a", "Lost", "a", "Saved", "q"])
        self.assertIn("Change was not applied", output)
        self.assertEqual(cli.engine.list_tasks(), [Task(1, "Saved")])

    def test_invalid_commands_ids_and_titles_do_not_save(self) -> None:
        storage = Mock(spec=TaskStorage)
        cli = TodoCLI(TodoEngine(), storage)
        output = self.run_cli(cli, ["unknown", "a", " ", "d", "abc", "c", "99", "q"])
        self.assertIn("Unknown command", output)
        self.assertIn("Error:", output)
        storage.save.assert_not_called()

    def test_eof_and_interrupt_exit_cleanly(self) -> None:
        for error in (EOFError, KeyboardInterrupt):
            with self.subTest(error=error):
                storage = Mock(spec=TaskStorage)
                output = io.StringIO()
                with patch("builtins.input", side_effect=error), patch("sys.stdout", output):
                    TodoCLI(TodoEngine(), storage).run()
                self.assertIn("Goodbye.", output.getvalue())
                storage.save.assert_not_called()

    def test_startup_storage_error_returns_failure_without_starting_ui(self) -> None:
        with patch("main.JsonStorage") as factory, patch("main.TodoCLI") as cli:
            factory.return_value.load.side_effect = StorageError("Corrupt file")
            with patch("sys.stderr", new_callable=io.StringIO) as output:
                self.assertEqual(main(), 1)
            self.assertIn("file was not changed", output.getvalue())
            cli.assert_not_called()
            factory.return_value.save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
