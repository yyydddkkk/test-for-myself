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

Report the length of the longest line with `--longest-line`:

```console
$ python3 wordcount.py --longest-line notes.txt
76
```

The file is decoded as UTF-8 and lengths are counted in Unicode code points,
not bytes, so `中文` is two characters. Line terminators (`\n` and `\r\n`) are
not part of the length, a final line without a trailing newline still counts,
and an empty file reports `0`.

A missing file prints an error to stderr and exits with status 2. With
`--longest-line`, a file that is not valid UTF-8 is reported the same way —
exit status 2, a short message on stderr, and nothing on stdout.
