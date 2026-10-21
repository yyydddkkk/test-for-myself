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


class LongestLineTest(unittest.TestCase):
    """Acceptance tests for --longest-line, all exercised through the CLI."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.directory = Path(tmp.name)

    def write_bytes(self, name, data):
        path = self.directory / name
        path.write_bytes(data)
        return path

    def assert_success(self, result, expected):
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, f"{expected}\n")
        self.assertEqual(result.stderr, "")

    def test_counts_longest_line_by_code_point(self):
        path = self.write_bytes("sample.txt", "中a\nabc\n".encode("utf-8"))

        self.assert_success(run("--longest-line", str(path)), 3)

    def test_empty_file_reports_zero(self):
        path = self.write_bytes("empty.txt", b"")

        self.assert_success(run("--longest-line", str(path)), 0)

    def test_counts_final_line_without_newline(self):
        path = self.write_bytes("sample.txt", b"ab\nabcd")

        self.assert_success(run("--longest-line", str(path)), 4)

    def test_excludes_line_terminators_from_length(self):
        path = self.write_bytes("sample.txt", b"abcd\n")

        self.assert_success(run("--longest-line", str(path)), 4)

    def test_multibyte_characters_count_once(self):
        path = self.write_bytes("chinese.txt", "中文中文\nab\n".encode("utf-8"))

        self.assert_success(run("--longest-line", str(path)), 4)

    def test_blank_line_does_not_win(self):
        path = self.write_bytes("sample.txt", b"a\n\nabc\n")

        self.assert_success(run("--longest-line", str(path)), 3)

    def test_missing_file_exits_2_without_stdout_or_traceback(self):
        path = self.directory / "missing.txt"

        result = run("--longest-line", str(path))

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("missing.txt", result.stderr)
        self.assertIn("No such file", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_invalid_utf8_exits_2_without_stdout_or_traceback(self):
        path = self.write_bytes("invalid.bin", b"\xff\n")

        result = run("--longest-line", str(path))

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("invalid.bin", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
