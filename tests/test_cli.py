"""Tests for configuration validation."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.main import main


class ConfigurationTests(unittest.TestCase):
    """Check valid configurations and all five user parameters."""

    def setUp(self):
        self.args = [
            "--package", "bash", "--source", "https://archive.ubuntu.com/ubuntu",
            "--version", "5.2.21-2ubuntu4", "--output", "graph.svg"
        ]

    def invoke(self, arguments):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            try:
                code = main(arguments)
            except SystemExit as error:
                code = error.code
        return code, output.getvalue()

    def test_valid_url(self):
        with patch(
            "src.main.read_apt_graph",
            return_value=({"bash": ["libc6"], "libc6": []}, [])
        ):
            code, output = self.invoke(self.args)
        self.assertEqual(code, 0)
        self.assertIn("package: bash", output)
        self.assertIn("test_mode: False", output)
        self.assertIn("output: graph.svg", output)

    def test_missing_package(self):
        code, _ = self.invoke(self.args[2:])
        self.assertNotEqual(code, 0)

    def test_invalid_package(self):
        args = self.args.copy()
        args[1] = "BAD NAME"
        code, _ = self.invoke(args)
        self.assertNotEqual(code, 0)

    def test_invalid_url(self):
        args = self.args.copy()
        args[3] = "file.txt"
        code, _ = self.invoke(args)
        self.assertNotEqual(code, 0)

    def test_invalid_version(self):
        args = self.args.copy()
        args[5] = "wrong/version"
        code, _ = self.invoke(args)
        self.assertNotEqual(code, 0)

    def test_invalid_output(self):
        args = self.args.copy()
        args[7] = "graph.png"
        code, _ = self.invoke(args)
        self.assertNotEqual(code, 0)

    def test_missing_test_file(self):
        args = self.args.copy()
        args[3] = "nonexistent-repo.txt"
        args.append("--test-mode")
        code, _ = self.invoke(args)
        self.assertNotEqual(code, 0)

    def test_valid_test_mode(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "repo.txt"
            file.write_text("A: B C\nB:\nC:\n", encoding="utf-8")
            args = self.args.copy()
            args[3] = str(file)
            args[1] = "a"
            args.append("--test-mode")
            code, output = self.invoke(args)
            self.assertEqual(code, 0)
            self.assertIn("test_mode: True", output)
            self.assertIn("A: B C", output)

    def test_test_mode_requires_file(self):
        args = self.args + ["--test-mode"]
        code, _ = self.invoke(args)
        self.assertNotEqual(code, 0)

    def test_no_arguments(self):
        code, _ = self.invoke([])
        self.assertNotEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
