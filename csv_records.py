"""Dependency-free RFC 4180 CSV parsing.

The grammar implemented here is the one published in RFC 4180::

    file        = [header CRLF] record *(CRLF record) [CRLF]
    record      = field *(COMMA field)
    field       = (escaped / non-escaped)
    escaped     = DQUOTE *(TEXTDATA / COMMA / CR / LF / 2DQUOTE) DQUOTE
    non-escaped = *TEXTDATA

Every character outside a quoted field is data except ``,``, CRLF and the
opening quote of a quoted field.  Spaces are data: they are never trimmed.
CR and LF inside a quoted field are preserved verbatim, including the CRLF
pair of an embedded line break.

``parse_csv`` is deliberately a little more permissive than the grammar in
two places, because real CSV files are commonly written that way:

* a bare LF terminates a record in addition to CRLF;
* any Unicode character is accepted as field data, not only the ASCII
  ``TEXTDATA`` range.

Malformed input raises :class:`ValueError` with the offset of the offending
character: an unterminated quoted field, a quote in the middle of an
unquoted field, a stray CR outside a quoted field, or anything other than a
comma or record terminator after a closing quote.
"""

__all__ = ["parse_csv"]


def parse_csv(text: str) -> list[list[str]]:
    """Parse ``text`` as RFC 4180 CSV and return its records.

    Each record is a list of fields in file order.  An empty input has no
    records and returns ``[]``.  A trailing record terminator does not add
    an empty record, while an empty line between records is a record with a
    single empty field.

    Raises:
        TypeError: if ``text`` is not :class:`str`.
        ValueError: if the quoting does not follow RFC 4180.
    """
    if not isinstance(text, str):
        raise TypeError(f"parse_csv() expects str, got {type(text).__name__}")

    records: list[list[str]] = []
    record: list[str] = []
    field: list[str] = []
    at_field_start = True
    in_quotes = False
    after_quote = False
    quote_start = 0
    i = 0
    n = len(text)

    while i < n:
        char = text[i]

        if in_quotes:
            if char == '"':
                if i + 1 < n and text[i + 1] == '"':
                    field.append('"')
                    i += 2
                    continue
                in_quotes = False
                after_quote = True
                i += 1
                continue
            field.append(char)
            i += 1
            continue

        if char == "\r":
            if i + 1 >= n or text[i + 1] != "\n":
                raise ValueError(
                    f"stray carriage return at offset {i}: "
                    "records are terminated by CRLF or LF"
                )
            i += 2
            record.append("".join(field))
            records.append(record)
            record = []
            field = []
            at_field_start = True
            after_quote = False
            continue

        if char == "\n":
            i += 1
            record.append("".join(field))
            records.append(record)
            record = []
            field = []
            at_field_start = True
            after_quote = False
            continue

        if after_quote:
            if char == ",":
                record.append("".join(field))
                field = []
                at_field_start = True
                after_quote = False
                i += 1
                continue
            raise ValueError(
                f"unexpected character {char!r} at offset {i}: "
                "only a comma or record terminator may follow a closing quote"
            )

        if char == ",":
            record.append("".join(field))
            field = []
            at_field_start = True
            i += 1
            continue

        if char == '"':
            if not at_field_start:
                raise ValueError(
                    f"unexpected quote at offset {i}: "
                    "a quoted field must start with a quote"
                )
            in_quotes = True
            quote_start = i
            at_field_start = False
            i += 1
            continue

        field.append(char)
        at_field_start = False
        i += 1

    if in_quotes:
        raise ValueError(
            f"unterminated quoted field starting at offset {quote_start}"
        )

    if record or not at_field_start or after_quote:
        record.append("".join(field))
        records.append(record)

    return records
