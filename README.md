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
