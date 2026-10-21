import unittest

from csv_records import parse_csv


class SeedTests(unittest.TestCase):
    def test_empty_input_has_no_records(self):
        self.assertEqual(parse_csv(""), [])

    def test_crlf_terminated_records(self):
        self.assertEqual(parse_csv("a,b\r\nc,d\r\n"), [["a", "b"], ["c", "d"]])

    def test_single_record_without_terminator(self):
        self.assertEqual(parse_csv("x,y"), [["x", "y"]])


class RecordTests(unittest.TestCase):
    def test_lf_terminates_records(self):
        self.assertEqual(parse_csv("a,b\nc,d\n"), [["a", "b"], ["c", "d"]])

    def test_trailing_terminator_adds_no_empty_record(self):
        self.assertEqual(parse_csv("a\r\n"), [["a"]])
        self.assertEqual(parse_csv("a\n"), [["a"]])

    def test_empty_line_is_a_record_with_one_empty_field(self):
        self.assertEqual(parse_csv("a\r\n\r\nb"), [["a"], [""], ["b"]])
        self.assertEqual(parse_csv("\r\n"), [[""]])

    def test_empty_fields(self):
        self.assertEqual(parse_csv("a,,b"), [["a", "", "b"]])
        self.assertEqual(parse_csv(","), [["", ""]])
        self.assertEqual(parse_csv("a,"), [["a", ""]])
        self.assertEqual(parse_csv(",a"), [["", "a"]])

    def test_spaces_are_preserved(self):
        self.assertEqual(parse_csv("a, b\r\n c ,d"), [["a", " b"], [" c ", "d"]])

    def test_unicode_data(self):
        self.assertEqual(parse_csv("héllo,世界"), [["héllo", "世界"]])

    def test_header_record_is_just_another_record(self):
        self.assertEqual(
            parse_csv("name,age\r\nAlice,30\r\n"),
            [["name", "age"], ["Alice", "30"]],
        )


class QuotedFieldTests(unittest.TestCase):
    def test_comma_inside_quotes_is_data(self):
        self.assertEqual(parse_csv('"a,b",c'), [["a,b", "c"]])

    def test_escaped_quotes(self):
        self.assertEqual(
            parse_csv('"He said ""hi""",x\r\n'),
            [['He said "hi"', "x"]],
        )

    def test_embedded_line_breaks_are_preserved(self):
        self.assertEqual(parse_csv('"a\r\nb",c'), [["a\r\nb", "c"]])
        self.assertEqual(parse_csv('"a\nb",c'), [["a\nb", "c"]])

    def test_empty_quoted_field(self):
        self.assertEqual(parse_csv('""'), [[""]])
        self.assertEqual(parse_csv('a,""'), [["a", ""]])

    def test_spaces_inside_quotes_are_preserved(self):
        self.assertEqual(parse_csv('" a ","b "'), [[" a ", "b "]])

    def test_quoted_field_in_middle_of_record(self):
        self.assertEqual(parse_csv('x,"a,b",y\r\n'), [["x", "a,b", "y"]])

    def test_quoted_field_at_record_boundaries(self):
        self.assertEqual(
            parse_csv('"a","b"\r\n"c","d"'),
            [["a", "b"], ["c", "d"]],
        )

    def test_quote_only_field(self):
        self.assertEqual(parse_csv('""""'), [['"']])


class MalformedInputTests(unittest.TestCase):
    def test_unterminated_quoted_field(self):
        with self.assertRaisesRegex(ValueError, r"offset 0"):
            parse_csv('"abc')

    def test_quote_inside_unquoted_field(self):
        with self.assertRaises(ValueError):
            parse_csv('a"b')

    def test_data_after_closing_quote(self):
        with self.assertRaises(ValueError):
            parse_csv('"a"b')

    def test_stray_carriage_return_outside_quotes(self):
        with self.assertRaises(ValueError):
            parse_csv("a\rb")

    def test_non_string_input(self):
        with self.assertRaises(TypeError):
            parse_csv(b"a,b")


if __name__ == "__main__":
    unittest.main()
