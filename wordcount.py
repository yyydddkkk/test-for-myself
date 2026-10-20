"""Count whitespace-separated words, lines or bytes in a file."""

import sys


def count_words(path):
    with open(path, encoding="utf-8") as handle:
        return len(handle.read().split())


def count_lines(path):
    with open(path, encoding="utf-8") as handle:
        return len(handle.read().splitlines())


def count_bytes(path):
    with open(path, "rb") as handle:
        return len(handle.read())


def main(argv):
    args = argv[1:]
    count = count_words
    if args and args[0] == "--lines":
        count = count_lines
        args = args[1:]
    elif args and args[0] == "--bytes":
        count = count_bytes
        args = args[1:]
    if len(args) != 1:
        print(f"usage: {argv[0]} [--lines | --bytes] FILE", file=sys.stderr)
        return 2
    path = args[0]
    try:
        result = count(path)
    except FileNotFoundError:
        print(f"{argv[0]}: {path}: No such file or directory", file=sys.stderr)
        return 2
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
