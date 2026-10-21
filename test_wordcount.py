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

    def test_bytes_counts_multibyte_utf8(self):
        path = self.directory / "chinese.txt"
        path.write_bytes(b"\xe4\xb8\xad\n")

        result = run("--bytes", str(path))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "4\n")
        self.assertEqual(result.stderr, "")

    def test_bytes_counts_invalid_utf8(self):
        path = self.directory / "invalid.bin"
        path.write_bytes(b"\xff\n")

        result = run("--bytes", str(path))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "2\n")
        self.assertEqual(result.stderr, "")

    def test_bytes_counts_empty_file_as_zero(self):
        path = self.directory / "empty.bin"
        path.write_bytes(b"")

        result = run("--bytes", str(path))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "0\n")
        self.assertEqual(result.stderr, "")

    def test_bytes_missing_file_exits_2_with_stderr_message(self):
        path = self.directory / "missing.bin"

        result = run("--bytes", str(path))

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("missing.bin", result.stderr)
        self.assertIn("No such file", result.stderr)

    def test_words_invalid_utf8_keeps_historical_failure(self):
        path = self.directory / "invalid.bin"
        path.write_bytes(b"\xff\n")

        result = run(str(path))

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("Traceback (most recent call last):", result.stderr)

    def test_lines_invalid_utf8_keeps_historical_failure(self):
        path = self.directory / "invalid.bin"
        path.write_bytes(b"\xff\n")

        result = run("--lines", str(path))

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("Traceback (most recent call last):", result.stderr)

    def test_chars_counts_unicode_code_points(self):
        path = self.directory / "chinese.txt"
        path.write_text("中a\n", encoding="utf-8")

        result = run("--chars", str(path))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "3\n")
        self.assertEqual(result.stderr, "")

    def test_chars_counts_spaces_tabs_and_newlines(self):
        path = self.directory / "whitespace.txt"
        path.write_text(" a \n\n b\t", encoding="utf-8")

        result = run("--chars", str(path))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "8\n")
        self.assertEqual(result.stderr, "")

    def test_chars_counts_empty_file_as_zero(self):
        path = self.directory / "empty.txt"
        path.write_text("", encoding="utf-8")

        result = run("--chars", str(path))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "0\n")
        self.assertEqual(result.stderr, "")

    def test_chars_missing_file_exits_2_with_stderr_message(self):
        path = self.directory / "missing.txt"

        result = run("--chars", str(path))

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("missing.txt", result.stderr)
        self.assertIn("No such file", result.stderr)

    def test_chars_invalid_utf8_exits_2_without_traceback(self):
        path = self.directory / "invalid.bin"
        path.write_bytes(b"\xff\n")

        result = run("--chars", str(path))

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("invalid UTF-8", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
