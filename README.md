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

Count raw bytes with `--bytes`, which reads the file as binary, so multi-byte
UTF-8 characters count once per encoded byte and invalid UTF-8 is counted
rather than rejected:

```console
$ python3 wordcount.py --bytes notes.txt
314
```

A missing file prints an error to stderr and exits with status 2.

## canonical_json

Serialize JSON-compatible Python values to the
[RFC 8785 JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785)
(JCS):

```python
from canonical_json import canonicalize

canonicalize({"b": 2, "a": 1})
# '{"a":1,"b":2}'
```

Object keys are sorted recursively by UTF-16 code unit order, insignificant
whitespace is dropped, strings keep ordinary Unicode literal, and numbers use
ECMAScript's shortest IEEE 754 representation. Array order is preserved.

For signing or hashing, encode the returned string as UTF-8:

```python
canonical_bytes = canonicalize(document).encode("utf-8")
```

Supported inputs are `dict`, `list`, `str`, `bool`, `None`, `int` and `float`.
The input must fit the I-JSON subset used by JCS:

- object keys must be strings;
- numbers must be finite and expressible as IEEE 754 doubles (so `NaN`,
  `Infinity` and integers that lose precision as doubles are rejected);
- strings must be valid Unicode, with no lone surrogates.

Tests:

```console
$ python3 -m unittest test_canonical_json
```
