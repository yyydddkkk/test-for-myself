"""Tests for IDNA2008 domain conversion."""

import unittest

from idna_domain import to_ascii


class BasicConversionTest(unittest.TestCase):
    def test_ascii_domain_is_unchanged(self):
        self.assertEqual(to_ascii("example.com"), "example.com")

    def test_unicode_label_is_punycoded(self):
        self.assertEqual(to_ascii("bücher.example"), "xn--bcher-kva.example")

    def test_multiple_unicode_labels(self):
        self.assertEqual(
            to_ascii("例え.テスト"), "xn--r8jz45g.xn--zckzah"
        )
        self.assertEqual(
            to_ascii("παράδειγμα.δοκιμή"),
            "xn--hxajbheg2az3al.xn--jxalpdlp",
        )

    def test_trailing_root_dot_is_preserved(self):
        self.assertEqual(to_ascii("example.com."), "example.com.")
        self.assertEqual(to_ascii("bücher.example."), "xn--bcher-kva.example.")

    def test_result_is_ascii_str(self):
        result = to_ascii("bücher.example")
        self.assertIsInstance(result, str)
        self.assertTrue(result.isascii())

    def test_conversion_is_idempotent(self):
        for domain in ("example.com", "bücher.example", "例え.テスト"):
            once = to_ascii(domain)
            self.assertEqual(to_ascii(once), once)


class IDNA2008NotIDNA2003Test(unittest.TestCase):
    def test_sharp_s_is_not_mapped_to_ss(self):
        # IDNA2003 maps U+00DF to "ss"; IDNA2008 keeps it.
        self.assertEqual(to_ascii("faß.de"), "xn--fa-hia.de")

    def test_final_sigma_is_preserved(self):
        # IDNA2003 case-folds final sigma to sigma.
        self.assertEqual(to_ascii("ς.example"), "xn--3xa.example")

    def test_uppercase_is_disallowed(self):
        with self.assertRaises(ValueError):
            to_ascii("Bücher.example")
        with self.assertRaises(ValueError):
            to_ascii("EXAMPLE.com")


class InvalidDomainTest(unittest.TestCase):
    def test_empty_domain(self):
        with self.assertRaises(ValueError):
            to_ascii("")

    def test_empty_labels(self):
        for domain in ("a..b", ".a", "a..", "example..com", "."):
            with self.assertRaises(ValueError):
                to_ascii(domain)

    def test_disallowed_characters(self):
        for domain in (
            "😀.example",
            "a_b.example",
            "a b.example",
            "a'b.example",
            "a/b.example",
            "a\u0000b.example",
        ):
            with self.assertRaises(ValueError):
                to_ascii(domain)

    def test_label_must_be_nfc(self):
        with self.assertRaises(ValueError):
            to_ascii("bu\u0308cher.example")

    def test_label_must_not_begin_with_combining_mark(self):
        with self.assertRaises(ValueError):
            to_ascii("\u0301abc.example")

    def test_hyphen_restrictions(self):
        for domain in (
            "-abc.example",
            "abc-.example",
            "ab--cd.example",
        ):
            with self.assertRaises(ValueError):
                to_ascii(domain)

    def test_label_too_long(self):
        with self.assertRaises(ValueError):
            to_ascii("a" * 64 + ".example")

    def test_domain_too_long(self):
        domain = ".".join(["a" * 63] * 4)
        self.assertEqual(len(domain), 255)
        with self.assertRaises(ValueError):
            to_ascii(domain)

    def test_maximum_lengths_are_accepted(self):
        label = "a" * 63
        self.assertEqual(to_ascii(label + ".example"), label + ".example")

        domain = ".".join(["a" * 63] * 3 + ["a" * 61])
        self.assertEqual(len(domain), 253)
        self.assertEqual(to_ascii(domain), domain)
        self.assertEqual(to_ascii(domain + "."), domain + ".")

        with self.assertRaises(ValueError):
            to_ascii(".".join(["a" * 63] * 3 + ["a" * 62]))

    def test_type_error_for_non_string(self):
        with self.assertRaises(TypeError):
            to_ascii(b"example.com")


class ALabelTest(unittest.TestCase):
    def test_valid_a_label_is_returned(self):
        self.assertEqual(
            to_ascii("xn--bcher-kva.example"), "xn--bcher-kva.example"
        )

    def test_malformed_a_labels_are_rejected(self):
        for domain in (
            "xn--.example",
            "xn--invalid-.example",
            "xn--abc.example",
            "xn--bad_value.example",
            "XN--bcher-kva.example",
        ):
            with self.assertRaises(ValueError):
                to_ascii(domain)


class ContextualRuleTest(unittest.TestCase):
    def test_middle_dot_requires_l_on_both_sides(self):
        self.assertEqual(to_ascii("l·l.cat"), "xn--ll-0ea.cat")
        with self.assertRaises(ValueError):
            to_ascii("a·b.cat")

    def test_greek_keraia_requires_following_greek(self):
        self.assertEqual(to_ascii("͵α.example"), "xn--wva4j.example")
        with self.assertRaises(ValueError):
            to_ascii("͵a.example")

    def test_hebrew_geresh_requires_preceding_hebrew(self):
        self.assertEqual(to_ascii("א׳.example"), "xn--4db4e.example")
        with self.assertRaises(ValueError):
            to_ascii("a׳.example")

    def test_katakana_middle_dot_requires_japanese_script(self):
        self.assertEqual(to_ascii("カ・ナ.example"), "xn--lck2c6g.example")
        with self.assertRaises(ValueError):
            to_ascii("a・b.example")

    def test_arabic_digit_sets_must_not_be_mixed(self):
        self.assertEqual(
            to_ascii("مثال١٢.example"), "xn--mgbh0fb7lg.example"
        )
        with self.assertRaises(ValueError):
            to_ascii("مثال١2.example")

    def test_joiner_requires_virama_or_joining_context(self):
        self.assertEqual(
            to_ascii("क्\u200dष.example"), "xn--11b2ezcw70k.example"
        )
        self.assertEqual(
            to_ascii("क्\u200cष.example"), "xn--11b2ezcs70k.example"
        )
        self.assertEqual(
            to_ascii("می\u200cخواهم.example"),
            "xn--mgbn2ecje63gr19l.example",
        )
        for domain in ("a\u200cb.example", "a\u200db.example"):
            with self.assertRaises(ValueError):
                to_ascii(domain)


class BidiRuleTest(unittest.TestCase):
    def test_valid_bidi_labels(self):
        self.assertEqual(
            to_ascii("مثال.إختبار"),
            "xn--mgbh0fb.xn--kgbechtv",
        )
        self.assertEqual(to_ascii("דוגמה.בדיקה"), "xn--6dbbec0c.xn--5dbedt4e")

    def test_arabic_indic_digit_first_is_rejected(self):
        # A right-to-left label must start with R or AL, not AN.
        with self.assertRaises(ValueError):
            to_ascii("١٢.example")

    def test_mixing_arabic_and_european_digits_is_rejected(self):
        with self.assertRaises(ValueError):
            to_ascii("مثال١2.example")

    def test_mixing_rtl_and_ltr_letters_is_rejected(self):
        with self.assertRaises(ValueError):
            to_ascii("مثال-abc.example")

    def test_ltr_labels_are_checked_in_a_bidi_domain(self):
        # RFC 5893 applies to every label once the domain has an RTL label.
        for domain in ("0à.א", "àˇ.א", "123.مثال", "مثال.123"):
            with self.assertRaises(ValueError):
                to_ascii(domain)

    def test_digit_leading_label_is_valid_without_rtl_labels(self):
        self.assertEqual(to_ascii("123.example"), "123.example")

    def test_valid_mixed_direction_domain(self):
        self.assertEqual(to_ascii("abc.א"), "abc.xn--4db")


if __name__ == "__main__":
    unittest.main()
