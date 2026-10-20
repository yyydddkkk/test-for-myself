"""Tests for the wordcount CLI."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("wordcount.py")


def run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
    )


class WordCountTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.directory = Path(tmp.name)

    def test_counts_whitespace_separated_words(self):
        path = self.directory / "sample.txt"
        path.write_text("one two\nthree four\tfive\n", encoding="utf-8")

        result = run(str(path))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "5\n")
        self.assertEqual(result.stderr, "")

    def test_lines_flag_counts_lines(self):
        path = self.directory / "sample.txt"
        path.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

        result = run("--lines", str(path))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "3\n")
        self.assertEqual(result.stderr, "")

    def test_empty_file_counts_zero(self):
        path = self.directory / "empty.txt"
        path.write_text("", encoding="utf-8")

        result = run(str(path))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "0\n")
        self.assertEqual(result.stderr, "")

    def test_missing_file_exits_2_with_stderr_message(self):
        path = self.directory / "missing.txt"

        result = run(str(path))

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("missing.txt", result.stderr)
        self.assertIn("No such file", result.stderr)


if __name__ == "__main__":
    unittest.main()
