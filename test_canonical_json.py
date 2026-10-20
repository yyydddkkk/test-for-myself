"""Tests for RFC 8785 canonical JSON serialization."""

import json
import math
import struct
import unittest

from canonical_json import canonicalize


def float_from_hex(bits):
    return struct.unpack(">d", bytes.fromhex(bits))[0]


class CanonicalizeStructureTest(unittest.TestCase):
    def test_seed_example_sorts_keys_and_removes_whitespace(self):
        self.assertEqual(canonicalize({"b": 2, "a": 1}), '{"a":1,"b":2}')

    def test_nested_objects_are_sorted_recursively(self):
        value = {"z": {"b": 1, "a": [{"d": 4, "c": 3}]}, "a": 0}

        self.assertEqual(
            canonicalize(value),
            '{"a":0,"z":{"a":[{"c":3,"d":4}],"b":1}}',
        )

    def test_array_order_is_preserved(self):
        self.assertEqual(canonicalize([3, 1, 2]), "[3,1,2]")

    def test_literals(self):
        self.assertEqual(canonicalize(None), "null")
        self.assertEqual(canonicalize(True), "true")
        self.assertEqual(canonicalize(False), "false")
        self.assertEqual(
            canonicalize([None, True, False]), "[null,true,false]"
        )

    def test_round_trips_through_standard_json_parser(self):
        value = {
            "numbers": [333333333.33333329, 1e30, 4.50, 2e-3],
            "text": "euro € and newline\n",
            "nested": [{"b": 2, "a": 1}],
        }

        self.assertEqual(json.loads(canonicalize(value)), value)

    def test_empty_containers(self):
        self.assertEqual(canonicalize({}), "{}")
        self.assertEqual(canonicalize([]), "[]")


class CanonicalizeStringTest(unittest.TestCase):
    def test_ordinary_unicode_stays_literal(self):
        self.assertEqual(canonicalize("€"), '"€"')
        self.assertEqual(canonicalize("😀"), '"😀"')
        self.assertEqual(canonicalize("\u2028\u2029"), '"\u2028\u2029"')

    def test_quote_and_backslash_are_escaped(self):
        self.assertEqual(canonicalize('"'), '"\\""')
        self.assertEqual(canonicalize("\\"), '"\\\\"')
        self.assertEqual(canonicalize("/"), '"/"')

    def test_control_characters_use_ecmascript_escapes(self):
        self.assertEqual(canonicalize("\b\t\n\f\r"), '"\\b\\t\\n\\f\\r"')
        self.assertEqual(canonicalize("\x00\x0b\x1f"), '"\\u0000\\u000b\\u001f"')
        self.assertEqual(canonicalize("\x7f"), '"\x7f"')

    def test_canonical_text_encodes_to_utf8(self):
        self.assertEqual(canonicalize("€").encode("utf-8"), b'"\xe2\x82\xac"')

    def test_lone_surrogates_are_rejected(self):
        with self.assertRaises(ValueError):
            canonicalize("\ud800")
        with self.assertRaises(ValueError):
            canonicalize({"\udc00": 1})

    def test_rfc_property_name_sort_order_uses_utf16_code_units(self):
        value = {
            "\u20ac": "Euro Sign",
            "\r": "Carriage Return",
            "\ufb33": "Hebrew Letter Dalet With Dagesh",
            "1": "One",
            "\U0001F600": "Emoji: Grinning Face",
            "\u0080": "Control",
            "\u00f6": "Latin Small Letter O With Diaeresis",
        }

        result = canonicalize(value)

        self.assertEqual(
            list(json.loads(result)),
            [
                "\r",
                "1",
                "\u0080",
                "\u00f6",
                "\u20ac",
                "\U0001F600",
                "\ufb33",
            ],
        )
        self.assertEqual(
            result,
            '{"\\r":"Carriage Return","1":"One","\u0080":"Control",'
            '"\u00f6":"Latin Small Letter O With Diaeresis",'
            '"\u20ac":"Euro Sign","\U0001F600":"Emoji: Grinning Face",'
            '"\ufb33":"Hebrew Letter Dalet With Dagesh"}',
        )

    def test_supplementary_character_sorts_before_some_bmp_characters(self):
        # U+10000 is UTF-16 D800 DC00, so it precedes U+E000 despite
        # having the larger code point.
        result = canonicalize({"\ue000": 1, "\U00010000": 2})

        self.assertEqual(result, '{"\U00010000":2,"\ue000":1}')


class CanonicalizeNumberTest(unittest.TestCase):
    # IEEE 754 bit patterns and expected output from RFC 8785 Appendix B.
    RFC_SAMPLES = [
        ("0000000000000000", "0"),
        ("8000000000000000", "0"),
        ("0000000000000001", "5e-324"),
        ("8000000000000001", "-5e-324"),
        ("7fefffffffffffff", "1.7976931348623157e+308"),
        ("ffefffffffffffff", "-1.7976931348623157e+308"),
        ("4340000000000000", "9007199254740992"),
        ("c340000000000000", "-9007199254740992"),
        ("4430000000000000", "295147905179352830000"),
        ("44b52d02c7e14af5", "9.999999999999997e+22"),
        ("44b52d02c7e14af6", "1e+23"),
        ("44b52d02c7e14af7", "1.0000000000000001e+23"),
        ("444b1ae4d6e2ef4e", "999999999999999700000"),
        ("444b1ae4d6e2ef4f", "999999999999999900000"),
        ("444b1ae4d6e2ef50", "1e+21"),
        ("3eb0c6f7a0b5ed8c", "9.999999999999997e-7"),
        ("3eb0c6f7a0b5ed8d", "0.000001"),
        ("41b3de4355555553", "333333333.3333332"),
        ("41b3de4355555554", "333333333.33333325"),
        ("41b3de4355555555", "333333333.3333333"),
        ("41b3de4355555556", "333333333.3333334"),
        ("41b3de4355555557", "333333333.33333343"),
        ("becbf647612f3696", "-0.0000033333333333333333"),
        ("43143ff3c1cb0959", "1424953923781206.2"),
    ]

    def test_rfc_8785_appendix_b_samples(self):
        for bits, expected in self.RFC_SAMPLES:
            with self.subTest(bits=bits):
                self.assertEqual(
                    canonicalize(float_from_hex(bits)), expected
                )

    def test_negative_zero_serializes_as_zero(self):
        self.assertEqual(canonicalize(-0.0), "0")
        self.assertEqual(canonicalize(0.0), "0")
        self.assertEqual(canonicalize(0), "0")

    def test_plain_integers(self):
        self.assertEqual(canonicalize(1), "1")
        self.assertEqual(canonicalize(-42), "-42")
        self.assertEqual(canonicalize(9007199254740991), "9007199254740991")
        self.assertEqual(canonicalize(-9007199254740991), "-9007199254740991")

    def test_large_ints_use_double_precision_representation(self):
        self.assertEqual(
            canonicalize(2 ** 68), "295147905179352830000"
        )

    def test_ints_not_representable_as_doubles_are_rejected(self):
        with self.assertRaises(ValueError):
            canonicalize(2 ** 53 + 1)
        with self.assertRaises(ValueError):
            canonicalize(10 ** 400)

    def test_nan_and_infinity_are_rejected(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    canonicalize(value)

    def test_small_and_large_magnitudes_switch_to_exponential(self):
        self.assertEqual(canonicalize(1e-6), "0.000001")
        self.assertEqual(canonicalize(1e-7), "1e-7")
        self.assertEqual(canonicalize(1.5e-7), "1.5e-7")
        self.assertEqual(canonicalize(1e20), "100000000000000000000")
        self.assertEqual(canonicalize(1e21), "1e+21")
        self.assertEqual(canonicalize(1e30), "1e+30")


class CanonicalizeInputValidationTest(unittest.TestCase):
    def test_unsupported_types_raise_type_error(self):
        for value in (b"bytes", (1, 2), {1, 2}, object()):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(TypeError):
                    canonicalize(value)

    def test_non_string_keys_raise_type_error(self):
        with self.assertRaises(TypeError):
            canonicalize({1: "one"})
        with self.assertRaises(TypeError):
            canonicalize({True: "yes"})


class CanonicalizeDocumentationExampleTest(unittest.TestCase):
    def test_rfc_8785_section_3_2_2_example(self):
        value = {
            "numbers": [
                333333333.33333329,
                1e30,
                4.50,
                2e-3,
                0.000000000000000000000000001,
            ],
            "string": "\u20ac$\u000f\u000aA'\u0042\u0022\u005c\\\"/",
            "literals": [None, True, False],
        }

        self.assertEqual(
            canonicalize(value),
            '{"literals":[null,true,false],'
            '"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27],'
            '"string":"€$\\u000f\\nA\'B\\"\\\\\\\\\\"/"}',
        )


if __name__ == "__main__":
    unittest.main()
