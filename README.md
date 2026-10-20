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
