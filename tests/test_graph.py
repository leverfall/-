"""Offline BFS, cycle, and test file regression checks."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.apt_repository import RepositoryError
from src.dependency_graph import bfs_graph, read_apt_graph, read_test_graph
from src.main import main


class GraphTests(unittest.TestCase):
    """Exercise directed graph traversal and malformed repositories."""

    def test_transitive_and_diamond(self):
        graph, order = bfs_graph(
            {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}, "A"
        )
        self.assertEqual(order, ["A", "B", "C", "D"])
        self.assertEqual(graph["C"], ["D"])

    def test_cycle(self):
        graph, order = bfs_graph({"A": ["B"], "B": ["A"]}, "A")
        self.assertEqual(order, ["A", "B"])
        self.assertEqual(graph["B"], ["A"])

    def test_self_loop(self):
        _, order = bfs_graph({"A": ["A"]}, "A")
        self.assertEqual(order, ["A"])

    def test_isolated(self):
        self.assertEqual(bfs_graph({"A": []}, "A"), ({"A": []}, ["A"]))

    def test_unknown_root(self):
        with self.assertRaises(RepositoryError):
            bfs_graph({"B": []}, "A")

    def test_unknown_dependency(self):
        with self.assertRaises(RepositoryError):
            bfs_graph({"A": ["B"]}, "A")

    def test_uppercase_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.txt"
            path.write_text("A: B C\nB: A\nC:\n", encoding="utf-8")
            graph = read_test_graph(path)
            self.assertEqual(bfs_graph(graph, "A")[1], ["A", "B", "C"])

    def test_lowercase_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.txt"
            path.write_text("A: b\nb:\n", encoding="utf-8")
            with self.assertRaises(RepositoryError):
                read_test_graph(path)

    def test_duplicate_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.txt"
            path.write_text("A: B\nA:\nB:\n", encoding="utf-8")
            with self.assertRaises(RepositoryError):
                read_test_graph(path)

    def test_missing_child_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.txt"
            path.write_text("A: B\n", encoding="utf-8")
            with self.assertRaises(RepositoryError):
                read_test_graph(path)

    @patch("src.dependency_graph.fetch_index")
    def test_apt_root_exact_version(self, fetch):
        fetch.return_value = (
            "Package: a\nVersion: 1\nDepends: x\n\n"
            "Package: a\nVersion: 2\nDepends: y\n\n"
            "Package: x\nVersion: 1\n\n"
            "Package: y\nVersion: 1\n\n"
        )
        graph, unresolved = read_apt_graph("https://example.org", "a", "2")
        self.assertEqual(bfs_graph(graph, "a")[1], ["a", "y"])
        self.assertEqual(unresolved, [])
        fetch.assert_called_once()

    @patch("src.dependency_graph.fetch_index")
    def test_apt_alternatives(self, fetch):
        fetch.return_value = (
            "Package: a\nVersion: 1\nDepends: missing | b, c (>= 1)\n\n"
            "Package: b\nVersion: 1\n\n"
        )
        graph, unresolved = read_apt_graph("https://example.org", "a", "1")
        self.assertEqual(graph["a"], ["b"])
        self.assertIn("a: c (>= 1)", unresolved)

    def test_cli_test_repo(self):
        args = ["--package", "A", "--source", "tests/example_repo.txt",
                "--test-mode", "--version", "1.0", "--output", "graph.svg"]
        self.assertEqual(main(args), 0)


if __name__ == "__main__":
    unittest.main()
