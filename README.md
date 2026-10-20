# test-for-myself

## wordcount

```console
usage: python3 wordcount.py [--lines | --bytes | --chars] FILE
```

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

Count Unicode characters with `--chars`, which counts code points, so a
multi-byte UTF-8 character such as `中` counts once and spaces and newlines
count too:

```console
$ python3 wordcount.py --chars notes.txt
314
```

A missing file prints an error to stderr and exits with status 2. Text modes
(`--chars`, `--lines` and the default word count) reject invalid UTF-8 with
status 2 and a short stderr message.
