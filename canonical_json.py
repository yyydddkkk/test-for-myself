"""Canonical JSON serialization per RFC 8785 (JCS).

``canonicalize(value)`` turns JSON-compatible Python data into the JSON
Canonicalization Scheme text defined by RFC 8785:

* object properties are sorted recursively by their raw names compared as
  UTF-16 code units;
* no insignificant whitespace is emitted;
* strings use the ECMAScript ``JSON.stringify`` escaping rules: only
  ``"``, ``\\`` and the ASCII control characters are escaped, and
  non-ASCII characters stay literal;
* numbers use the ECMAScript number-to-string algorithm (IEEE 754 double
  precision, shortest round-trip representation);
* ``null``, ``true`` and ``false`` are lowercase.

The result is a :class:`str`.  Encode it as UTF-8 to obtain the canonical
byte sequence used for hashing or signing.
"""

import math

__all__ = ["canonicalize"]

_ESCAPES = {
    '"': '\\"',
    "\\": "\\\\",
    "\b": "\\b",
    "\t": "\\t",
    "\n": "\\n",
    "\f": "\\f",
    "\r": "\\r",
}


def canonicalize(value):
    """Return the RFC 8785 canonical JSON representation of *value*.

    Supported values are ``dict``, ``list``, ``str``, ``bool``, ``None``,
    ``int`` and ``float``.  Object keys must be strings.  Input must be
    expressible as I-JSON: no ``NaN``/``Infinity``, no integers that are
    not exactly representable as IEEE 754 doubles, and no lone surrogate
    code points in strings.

    Raises:
        TypeError: for unsupported Python types or non-string keys.
        ValueError: for values that RFC 8785 does not permit.
    """
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return _quote(value)
    if isinstance(value, int):
        return _format_number(value)
    if isinstance(value, float):
        return _format_number(value)
    if isinstance(value, list):
        return "[" + ",".join(canonicalize(item) for item in value) + "]"
    if isinstance(value, dict):
        return _serialize_object(value)
    raise TypeError(
        "cannot canonicalize value of type "
        f"{type(value).__name__}: {value!r}"
    )


def _serialize_object(value):
    keys = list(value)
    for key in keys:
        if not isinstance(key, str):
            raise TypeError(
                "JSON object keys must be strings, "
                f"got {type(key).__name__}: {key!r}"
            )
        _check_unicode(key)
    # RFC 8785 section 3.2.3: compare raw property names as arrays of
    # UTF-16 code units.  Big-endian UTF-16 bytes preserve that ordering.
    keys.sort(key=lambda key: key.encode("utf-16-be"))
    return (
        "{"
        + ",".join(
            _quote(key) + ":" + canonicalize(value[key]) for key in keys
        )
        + "}"
    )


def _check_unicode(text):
    try:
        text.encode("utf-16-be")
    except UnicodeEncodeError as exc:
        raise ValueError(
            "JCS requires valid Unicode strings; "
            f"lone surrogates are not permitted: {text!r}"
        ) from exc


def _quote(text):
    _check_unicode(text)
    parts = ['"']
    for char in text:
        escaped = _ESCAPES.get(char)
        if escaped is not None:
            parts.append(escaped)
        elif char < "\x20":
            parts.append("\\u%04x" % ord(char))
        else:
            parts.append(char)
    parts.append('"')
    return "".join(parts)


def _format_number(value):
    """Serialize an int or float like ECMAScript's Number::toString."""
    if isinstance(value, int):
        try:
            as_float = float(value)
        except OverflowError:
            raise ValueError(
                "JCS numbers must be expressible as IEEE 754 doubles; "
                f"{value!r} is out of range"
            ) from None
        if int(as_float) != value:
            raise ValueError(
                "JCS numbers must be expressible as IEEE 754 doubles; "
                f"{value!r} is not"
            )
        value = as_float
    elif not math.isfinite(value):
        raise ValueError(
            f"JCS does not permit NaN or Infinity: {value!r}"
        )

    # NaN/Infinity are already rejected; both zeros serialize as "0".
    if value == 0:
        return "0"

    sign = ""
    if value < 0:
        sign = "-"
        value = -value

    text = repr(value)
    if "e" in text:
        mantissa, exponent_text = text.split("e")
        exponent = int(exponent_text)
    else:
        mantissa = text
        exponent = 0

    if "." in mantissa:
        integer_part, fraction_part = mantissa.split(".")
    else:
        integer_part, fraction_part = mantissa, ""

    digits = integer_part + fraction_part
    # n is the position of the decimal point relative to the first digit:
    # value == int(digits) * 10 ** (n - len(digits)), with no leading zeros.
    n = len(integer_part) + exponent
    stripped = digits.lstrip("0")
    n -= len(digits) - len(stripped)
    digits = stripped.rstrip("0")
    k = len(digits)

    # Layout rules from ECMAScript 7.1.12.1, preserving shortest digits.
    if k <= n <= 21:
        body = digits + "0" * (n - k)
    elif 0 < n <= 21:
        body = digits[:n] + "." + digits[n:]
    elif -6 < n <= 0:
        body = "0." + "0" * (-n) + digits
    else:
        scientific_exponent = n - 1
        coefficient = digits if k == 1 else digits[0] + "." + digits[1:]
        sign_char = "+" if scientific_exponent >= 0 else "-"
        body = f"{coefficient}e{sign_char}{abs(scientific_exponent)}"

    return sign + body
