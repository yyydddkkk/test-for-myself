"""Convert Unicode domain names to ASCII (A-label) form under IDNA2008.

The public entry point is :func:`to_ascii`.  Labels are validated against
the IDNA2008 rules (RFC 5890-5893):

* the derived code point properties of RFC 5892 (PVALID, CONTEXTJ,
  CONTEXTO, DISALLOWED, UNASSIGNED), calculated from the Unicode database
  shipped with Python;
* the contextual rules of RFC 5892 Appendix A for joiners, middle dot,
  Greek keraia, Hebrew punctuation, Katakana middle dot, and Arabic-Indic
  digits;
* the label rules of RFC 5891 (NFC, hyphen restrictions, no leading
  combining mark, label length);
* the Bidi Rule of RFC 5893, applied to every label when the domain
  contains a right-to-left label.

IDNA2008 defines no case mapping or compatibility mapping, so this module
performs neither: input must already be in NFC and use the canonical
(lowercase) spellings of letters.  A-labels must already be lowercase;
valid A-labels are validated and returned unchanged.

Only U+002E FULL STOP separates labels.  A single trailing root dot is
preserved; empty labels are rejected.
"""

from __future__ import annotations

import unicodedata

_ACE_PREFIX = "xn--"
_MAX_LABEL_LENGTH = 63
_MAX_DOMAIN_LENGTH = 253
_MAX_INPUT_LENGTH = 1024

_LETTER_DIGITS = frozenset({"Ll", "Lu", "Lo", "Nd", "Lm", "Mn", "Mc"})
_RTL_CATEGORIES = frozenset({"R", "AL", "AN"})
_LTR_ALLOWED = frozenset({"L", "EN", "ES", "CS", "ET", "ON", "BN", "NSM"})
_LTR_ENDING = frozenset({"L", "EN"})
_RTL_ALLOWED = frozenset({"R", "AL", "AN", "EN", "ES", "CS", "ET", "ON", "BN", "NSM"})
_RTL_ENDING = frozenset({"R", "AL", "EN", "AN"})

# RFC 5892 Section 2.6: code points whose derived property is fixed by the
# standard rather than computed from Unicode properties.
_EXCEPTIONS = {
    0x00DF: "PVALID",
    0x03C2: "PVALID",
    0x06FD: "PVALID",
    0x06FE: "PVALID",
    0x0F0B: "PVALID",
    0x3007: "PVALID",
    0x00B7: "CONTEXTO",
    0x0375: "CONTEXTO",
    0x05F3: "CONTEXTO",
    0x05F4: "CONTEXTO",
    0x30FB: "CONTEXTO",
    **{cp: "CONTEXTO" for cp in range(0x0660, 0x066A)},
    **{cp: "CONTEXTO" for cp in range(0x06F0, 0x06FA)},
    0x0640: "DISALLOWED",
    0x07FA: "DISALLOWED",
    0x302E: "DISALLOWED",
    0x302F: "DISALLOWED",
    0x3031: "DISALLOWED",
    0x3032: "DISALLOWED",
    0x3033: "DISALLOWED",
    0x3034: "DISALLOWED",
    0x3035: "DISALLOWED",
    0x303B: "DISALLOWED",
}


def _ranges(spec: str) -> tuple[tuple[int, int], ...]:
    """Parse a space-separated ``START-END`` hex range list."""
    parsed = []
    for item in spec.split():
        start, end = item.split("-")
        parsed.append((int(start, 16), int(end, 16)))
    return tuple(parsed)


def _in_ranges(cp: int, ranges: tuple[tuple[int, int], ...]) -> bool:
    for start, end in ranges:
        if cp < start:
            return False
        if cp <= end:
            return True
    return False


# Default_Ignorable_Code_Point (DerivedCoreProperties.txt).
_DEFAULT_IGNORABLE = _ranges(
    "00AD-00AD 034F-034F 061C-061C 115F-1160 17B4-17B5 180B-180F "
    "200B-200F 202A-202E 2060-206F 3164-3164 FE00-FE0F FEFF-FEFF "
    "FFA0-FFA0 FFF0-FFF8 1BCA0-1BCA3 1D173-1D17A E0000-E0FFF"
)
# White_Space (PropList.txt).
_WHITE_SPACE = _ranges(
    "0009-000D 0020-0020 0085-0085 00A0-00A0 1680-1680 "
    "2000-200A 2028-2029 202F-202F 205F-205F 3000-3000"
)
# Blocks: Combining Diacritical Marks for Symbols, Musical Symbols,
# Ancient Greek Musical Notation.
_IGNORABLE_BLOCKS = _ranges("20D0-20FF 1D100-1D1FF 1D200-1D24F")
# Hangul_Syllable_Type L, V, T (conjoining Jamo).
_OLD_HANGUL_JAMO = _ranges(
    "1100-115F 1160-11A7 11A8-11FF A960-A97C D7B0-D7C6 D7CB-D7FB"
)

# Script and Joining_Type data required by RFC 5892 Appendix A.  Unicode
# does not expose these through :mod:`unicodedata`, so the ranges are
# embedded.  Joining_Type T is derived from the Mn, Me and Cf categories,
# with the exceptions below.
_GREEK = _ranges(
    "0370-0373 0375-0377 037A-037D 037F-037F 0384-0384 0386-0386 "
    "0388-038A 038C-038C 038E-03A1 03A3-03E1 03F0-03FF 1D26-1D2A "
    "1D5D-1D61 1D66-1D6A 1DBF-1DBF 1F00-1F15 1F18-1F1D 1F20-1F45 "
    "1F48-1F4D 1F50-1F57 1F59-1F59 1F5B-1F5B 1F5D-1F5D 1F5F-1F7D "
    "1F80-1FB4 1FB6-1FC4 1FC6-1FD3 1FD6-1FDB 1FDD-1FEF 1FF2-1FF4 "
    "1FF6-1FFE 2126-2126 AB65-AB65 10140-1018E 101A0-101A0 "
    "1D200-1D245 1DFF3-1DFF4"
)
_HEBREW = _ranges(
    "0591-05C9 05D0-05EA 05EF-05F4 FB1D-FB36 FB38-FB3C FB3E-FB3E "
    "FB40-FB41 FB43-FB44 FB46-FB4F"
)
_HIRAGANA = _ranges(
    "3041-3096 309D-309F 1B001-1B11F 1B123-1B123 1B132-1B132 "
    "1B150-1B152 1F200-1F200"
)
_KATAKANA = _ranges(
    "30A1-30FA 30FD-30FF 31F0-31FF 32D0-32FE 3300-3357 FF66-FF6F "
    "FF71-FF9D 1AFF0-1AFF3 1AFF5-1AFFB 1AFFD-1AFFE 1B000-1B000 "
    "1B120-1B122 1B124-1B128 1B155-1B155 1B164-1B168"
)
_HAN = _ranges(
    "2E80-2E99 2E9B-2EF3 2F00-2FD5 3005-3005 3007-3007 3021-3029 "
    "3038-303B 3400-4DBF 4E00-9FFF F900-FA6D FA70-FAD9 16FE2-16FE3 "
    "16FF0-16FF6 20000-2A6DF 2A700-2B81E 2B820-2CEAD 2CEB0-2EBE0 "
    "2EBF0-2EE5D 2F800-2FA1D 30000-3134A 31350-33479"
)
_JOINING_D = _ranges(
    "0620-0620 0626-0626 0628-0628 062A-062E 0633-063F 0641-0647 "
    "0649-064A 066E-066F 0678-0687 069A-06BF 06C1-06C2 06CC-06CC "
    "06CE-06CE 06D0-06D1 06FA-06FC 06FF-06FF 0712-0714 071A-071D "
    "071F-0727 0729-0729 072B-072B 072D-072E 074E-0758 075C-076A "
    "076D-0770 0772-0772 0775-0777 077A-077F 07CA-07EA 0841-0845 "
    "0848-0848 084A-0853 0855-0855 0860-0860 0862-0865 0868-0868 "
    "0886-0886 0889-088D 088F-088F 08A0-08A9 08AF-08B0 08B3-08B8 "
    "08BA-08C8 1807-1807 1820-1878 1887-18A8 18AA-18AA A840-A871 "
    "10AC0-10AC4 10AD3-10AD6 10AD8-10ADC 10ADE-10AE0 10AEB-10AEE "
    "10B80-10B80 10B82-10B82 10B86-10B88 10B8A-10B8B 10B8D-10B8D "
    "10B90-10B90 10BAD-10BAE 10D01-10D21 10D23-10D23 10EC3-10EC4 "
    "10EC6-10EC7 10F30-10F32 10F34-10F44 10F51-10F53 10F70-10F73 "
    "10F76-10F81 10FB0-10FB0 10FB2-10FB3 10FB8-10FB8 10FBB-10FBC "
    "10FBE-10FBF 10FC1-10FC1 10FC4-10FC4 10FCA-10FCA 1E900-1E943"
)
_JOINING_L = _ranges(
    "A872-A872 10ACD-10ACD 10AD7-10AD7 10D00-10D00 10ED9-10EEE 10FCB-10FCB"
)
_JOINING_R = _ranges(
    "0622-0625 0627-0627 0629-0629 062F-0632 0648-0648 0671-0673 "
    "0675-0677 0688-0699 06C0-06C0 06C3-06CB 06CD-06CD 06CF-06CF "
    "06D2-06D3 06D5-06D5 06EE-06EF 0710-0710 0715-0719 071E-071E "
    "0728-0728 072A-072A 072C-072C 072F-072F 074D-074D 0759-075B "
    "076B-076C 0771-0771 0773-0774 0778-0779 0840-0840 0846-0847 "
    "0849-0849 0854-0854 0856-0858 0867-0867 0869-086A 0870-0882 "
    "088E-088E 08AA-08AC 08AE-08AE 08B1-08B2 08B9-08B9 10AC5-10AC5 "
    "10AC7-10AC7 10AC9-10ACA 10ACE-10AD2 10ADD-10ADD 10AE1-10AE1 "
    "10AE4-10AE4 10AEF-10AEF 10B81-10B81 10B83-10B85 10B89-10B89 "
    "10B8C-10B8C 10B8E-10B8F 10B91-10B91 10BA9-10BAC 10D22-10D22 "
    "10EC2-10EC2 10F33-10F33 10F54-10F54 10F74-10F75 10FB4-10FB6 "
    "10FB9-10FBA 10FBD-10FBD 10FC2-10FC3 10FC9-10FC9"
)
# Cf characters that are not Joining_Type T, plus the one Lm character
# that is transparent, and the joiners themselves.
_NOT_TRANSPARENT = frozenset(
    {
        0x0600, 0x0601, 0x0602, 0x0603, 0x0604, 0x0605, 0x06DD,
        0x0890, 0x0891, 0x08E2, 0x180E, 0x200C, 0x200D, 0x2066,
        0x2067, 0x2068, 0x2069, 0x1171E, 0x110BD, 0x110CD,
    }
)
_TRANSPARENT_LM = 0x1E94B


def _is_noncharacter(cp: int) -> bool:
    return 0xFDD0 <= cp <= 0xFDEF or cp & 0xFFFE == 0xFFFE


def _derived_property(cp: int) -> str:
    """Return the RFC 5892 derived property value for ``cp``."""
    if cp in _EXCEPTIONS:
        return _EXCEPTIONS[cp]

    category = unicodedata.category(chr(cp))
    if category == "Cs":
        return "DISALLOWED"
    if category == "Cn" and not _is_noncharacter(cp):
        return "UNASSIGNED"
    if cp == 0x2D or 0x30 <= cp <= 0x39 or 0x61 <= cp <= 0x7A:
        return "PVALID"
    if cp in (0x200C, 0x200D):
        return "CONTEXTJ"

    char = chr(cp)
    folded = unicodedata.normalize("NFKC", char).casefold()
    if unicodedata.normalize("NFKC", folded) != char:
        return "DISALLOWED"
    if (
        _in_ranges(cp, _DEFAULT_IGNORABLE)
        or _in_ranges(cp, _WHITE_SPACE)
        or _is_noncharacter(cp)
    ):
        return "DISALLOWED"
    if _in_ranges(cp, _IGNORABLE_BLOCKS) or _in_ranges(cp, _OLD_HANGUL_JAMO):
        return "DISALLOWED"
    if category in _LETTER_DIGITS:
        return "PVALID"
    return "DISALLOWED"


def _joining_type(cp: int) -> str | None:
    """Return Joining_Type for ``cp`` when it matters to RFC 5892."""
    if _in_ranges(cp, _JOINING_D):
        return "D"
    if _in_ranges(cp, _JOINING_L):
        return "L"
    if _in_ranges(cp, _JOINING_R):
        return "R"
    if cp == _TRANSPARENT_LM:
        return "T"
    if cp in _NOT_TRANSPARENT:
        return None
    if unicodedata.category(chr(cp)) in ("Mn", "Me", "Cf"):
        return "T"
    return None


def _is_script(cp: int, ranges: tuple[tuple[int, int], ...]) -> bool:
    return _in_ranges(cp, ranges)


def _valid_contextj(label: str, pos: int) -> bool:
    cp = ord(label[pos])
    if cp == 0x200D:
        return pos > 0 and unicodedata.combining(label[pos - 1]) == 9

    # U+200C ZERO WIDTH NON-JOINER.
    if pos > 0 and unicodedata.combining(label[pos - 1]) == 9:
        return True
    before = pos - 1
    while before >= 0 and _joining_type(ord(label[before])) == "T":
        before -= 1
    if before < 0 or _joining_type(ord(label[before])) not in ("L", "D"):
        return False
    after = pos + 1
    while after < len(label) and _joining_type(ord(label[after])) == "T":
        after += 1
    return after < len(label) and _joining_type(ord(label[after])) in ("R", "D")


def _valid_contexto(label: str, pos: int) -> bool:
    cp = ord(label[pos])
    if cp == 0x00B7:
        return (
            0 < pos < len(label) - 1
            and ord(label[pos - 1]) == 0x006C
            and ord(label[pos + 1]) == 0x006C
        )
    if cp == 0x0375:
        return pos + 1 < len(label) and _is_script(ord(label[pos + 1]), _GREEK)
    if cp in (0x05F3, 0x05F4):
        return pos > 0 and _is_script(ord(label[pos - 1]), _HEBREW)
    if cp == 0x30FB:
        return any(
            _is_script(ord(char), _HIRAGANA)
            or _is_script(ord(char), _KATAKANA)
            or _is_script(ord(char), _HAN)
            for char in label
            if char != "\u30fb"
        )
    if 0x0660 <= cp <= 0x0669:
        return not any(0x06F0 <= ord(char) <= 0x06F9 for char in label)
    if 0x06F0 <= cp <= 0x06F9:
        return not any(0x0660 <= ord(char) <= 0x0669 for char in label)
    return False


def _check_bidi(label: str, check_ltr: bool = False) -> None:
    directions = [unicodedata.bidirectional(char) for char in label]
    if not check_ltr and not any(
        direction in _RTL_CATEGORIES for direction in directions
    ):
        return

    first = directions[0]
    if first in ("R", "AL"):
        rtl = True
    elif first == "L":
        rtl = False
    else:
        raise ValueError(f"label {label!r} must start with a letter for Bidi")

    if rtl:
        if any(direction not in _RTL_ALLOWED for direction in directions):
            raise ValueError(f"label {label!r} violates the Bidi rule")
        numbers = {d for d in directions if d in ("AN", "EN")}
        if len(numbers) > 1:
            raise ValueError(f"label {label!r} mixes Arabic and European digits")
        ending = _RTL_ENDING
    else:
        if any(direction not in _LTR_ALLOWED for direction in directions):
            raise ValueError(f"label {label!r} violates the Bidi rule")
        ending = _LTR_ENDING

    end = len(directions)
    while end > 0 and directions[end - 1] == "NSM":
        end -= 1
    if end == 0 or directions[end - 1] not in ending:
        raise ValueError(f"label {label!r} ends with an invalid Bidi character")


def _check_label(label: str) -> None:
    """Validate one U-label (or ASCII LDH label) under IDNA2008.

    The Bidi Rule is applied separately at domain level in :func:`to_ascii`.
    """
    if not label:
        raise ValueError("empty label")
    if len(label) > _MAX_LABEL_LENGTH:
        raise ValueError(f"label {label!r} is too long")

    if unicodedata.normalize("NFC", label) != label:
        raise ValueError(f"label {label!r} is not in NFC")
    if label[2:4] == "--":
        raise ValueError(f"label {label!r} has hyphens in positions 3 and 4")
    if label.startswith("-") or label.endswith("-"):
        raise ValueError(f"label {label!r} starts or ends with a hyphen")
    if unicodedata.category(label[0]).startswith("M"):
        raise ValueError(f"label {label!r} starts with a combining mark")

    for pos, char in enumerate(label):
        prop = _derived_property(ord(char))
        if prop == "PVALID":
            continue
        if prop == "CONTEXTJ":
            if _valid_contextj(label, pos):
                continue
            raise ValueError(
                f"joiner U+{ord(char):04X} is not allowed at position {pos + 1}"
                f" of {label!r}"
            )
        if prop == "CONTEXTO":
            if _valid_contexto(label, pos):
                continue
            raise ValueError(
                f"code point U+{ord(char):04X} is not allowed in context at"
                f" position {pos + 1} of {label!r}"
            )
        if prop == "UNASSIGNED":
            raise ValueError(f"label {label!r} contains an unassigned code point")
        raise ValueError(
            f"label {label!r} contains disallowed code point U+{ord(char):04X}"
        )


def _is_rtl_label(label: str) -> bool:
    return any(
        unicodedata.bidirectional(char) in _RTL_CATEGORIES for char in label
    )


def _encode_label(label: str) -> str:
    """Return the A-label for a validated U-label."""
    if label.isascii():
        return label
    encoded = _ACE_PREFIX + label.encode("punycode").decode("ascii")
    if len(encoded) > _MAX_LABEL_LENGTH:
        raise ValueError(f"label {label!r} is too long in ASCII form")
    return encoded


def _parse_ascii_label(label: str) -> tuple[str, str]:
    """Validate an ASCII label and return ``(u_label, a_label)``."""
    if not label.startswith(_ACE_PREFIX):
        _check_label(label)
        return label, label

    if label != label.lower():
        raise ValueError(f"A-label {label!r} must be lowercase")
    if len(label) > _MAX_LABEL_LENGTH:
        raise ValueError(f"A-label {label!r} is too long")
    body = label[len(_ACE_PREFIX) :]
    if not body or body.endswith("-"):
        raise ValueError(f"malformed A-label {label!r}")
    if any(not ("a" <= char <= "z" or "0" <= char <= "9" or char == "-") for char in label):
        raise ValueError(f"malformed A-label {label!r}")

    try:
        u_label = body.encode("ascii").decode("punycode")
    except UnicodeError as exc:
        raise ValueError(f"malformed A-label {label!r}") from exc
    if not u_label:
        raise ValueError(f"malformed A-label {label!r}")

    _check_label(u_label)
    if _encode_label(u_label) != label:
        raise ValueError(f"A-label {label!r} is not in canonical form")
    return u_label, label


def to_ascii(domain: str) -> str:
    """Convert a Unicode domain name to its IDNA2008 ASCII (A-label) form.

    :param domain: A domain name in Unicode.  Labels must already be in NFC
        and use IDNA2008-valid spellings; no case or compatibility mapping
        is performed.
    :returns: The domain in ASCII form, with a preserved trailing dot.
    :raises TypeError: If ``domain`` is not a string.
    :raises ValueError: If the domain or any label is not valid under
        IDNA2008.
    """
    if not isinstance(domain, str):
        raise TypeError("domain must be a str")
    if not domain:
        raise ValueError("empty domain")
    if len(domain) > _MAX_INPUT_LENGTH:
        raise ValueError("domain is too long")

    trailing_dot = domain.endswith(".")
    body = domain[:-1] if trailing_dot else domain
    if not body:
        raise ValueError("empty domain")

    labels = body.split(".")
    if any(label == "" for label in labels):
        raise ValueError("domain contains an empty label")

    parsed_labels = []
    for label in labels:
        if label.isascii():
            parsed_labels.append(_parse_ascii_label(label))
        else:
            _check_label(label)
            parsed_labels.append((label, _encode_label(label)))

    # RFC 5893 applies the Bidi Rule to every label of a Bidi domain name,
    # including LTR and pure-ASCII labels.
    rtl_domain = any(_is_rtl_label(u_label) for u_label, _ in parsed_labels)
    for u_label, _ in parsed_labels:
        _check_bidi(u_label, check_ltr=rtl_domain)

    result = ".".join(ascii_label for _, ascii_label in parsed_labels)
    if len(result) > _MAX_DOMAIN_LENGTH:
        raise ValueError("domain is too long")
    return result + "." if trailing_dot else result
