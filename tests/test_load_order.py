"""Tests for dependency-first ordering and stage-4 CLI behavior."""

import contextlib
import io
import unittest

from src.apt_repository import RepositoryError
from src.load_order import dependency_load_order
from src.main import main


class LoadOrderTests(unittest.TestCase):
    """Confirm a valid topological order or a clear cycle explanation."""

    def test_diamond(self):
        graph = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
        self.assertEqual(dependency_load_order(graph), ["D", "B", "C", "A"])

    def test_chain(self):
        graph = {"A": ["B"], "B": ["C"], "C": []}
        self.assertEqual(dependency_load_order(graph), ["C", "B", "A"])

    def test_isolated(self):
        self.assertEqual(dependency_load_order({"A": []}), ["A"])

    def test_cycle(self):
        with self.assertRaisesRegex(RepositoryError, "цикл"):
            dependency_load_order({"A": ["B"], "B": ["A"]})

    def test_self_cycle(self):
        with self.assertRaisesRegex(RepositoryError, "цикл"):
            dependency_load_order({"A": ["A"]})

    def test_missing_dependency(self):
        with self.assertRaisesRegex(RepositoryError, "нет описания"):
            dependency_load_order({"A": ["B"]})

    def test_duplicate_edges(self):
        self.assertEqual(
            dependency_load_order({"A": ["B", "B"], "B": []}),
            ["B", "A"],
        )

    def test_cli_load_order(self):
        args = ["--package", "A", "--source", "tests/example_repo.txt",
                "--test-mode", "--version", "1.0", "--output", "graph.svg",
                "--load-order"]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(args), 0)
        self.assertIn("Порядок загрузки: D -> B -> C -> A", output.getvalue())

    def test_cli_cycle_message(self):
        args = ["--package", "A", "--source", "tests/cycle_repo.txt",
                "--test-mode", "--version", "1.0", "--output", "graph.svg",
                "--load-order"]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(args), 0)
        self.assertIn("Порядок загрузки недоступен", output.getvalue())
        self.assertIn("цикл", output.getvalue())


if __name__ == "__main__":
    unittest.main()
