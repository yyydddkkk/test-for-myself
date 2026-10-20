# test-for-myself

## wordcount

Count whitespace-separated words in a file:

```console
$ python3 wordcount.py notes.txt
42
```

Count lines instead, with `--lines`:

```console
$ python3 wordcount.py --lines notes.txt
7
```

A missing file prints an error to stderr and exits with status 2.

## idna_domain

Convert a Unicode domain name to its IDNA2008 ASCII (A-label) form:

```python
>>> from idna_domain import to_ascii
>>> to_ascii("example.com")
'example.com'
>>> to_ascii("bücher.example")
'xn--bcher-kva.example'
```

`to_ascii` validates every label against RFC 5890-5893, including the
RFC 5892 derived code point properties, contextual rules, label syntax and
the Bidi Rule, and raises `ValueError` for an invalid label:

```python
>>> to_ascii("a..b")
Traceback (most recent call last):
    ...
ValueError: domain contains an empty label
>>> to_ascii("😀.example")
Traceback (most recent call last):
    ...
ValueError: label '😀' contains disallowed code point U+1F600
```

IDNA2008 performs no case or compatibility mapping, so input must already be
in lowercase NFC. A single trailing root dot is preserved. Only `U+002E`
separates labels. Existing A-labels are validated and returned in canonical
lowercase form.
