"""Count whitespace-separated words, lines or bytes in a file."""

import sys


class InvalidUtf8(Exception):
    """Raised by --longest-line when the file is not valid UTF-8."""


def count_words(path):
    with open(path, encoding="utf-8") as handle:
        return len(handle.read().split())


def count_lines(path):
    with open(path, encoding="utf-8") as handle:
        return len(handle.read().splitlines())


def count_bytes(path):
    with open(path, "rb") as handle:
        return len(handle.read())


def count_longest_line(path):
    try:
        with open(path, encoding="utf-8") as handle:
            lengths = [len(line) for line in handle.read().splitlines()]
    except UnicodeDecodeError as exc:
        raise InvalidUtf8(str(exc)) from exc
    return max(lengths, default=0)


def main(argv):
    args = argv[1:]
    count = count_words
    if args and args[0] == "--lines":
        count = count_lines
        args = args[1:]
    elif args and args[0] == "--bytes":
        count = count_bytes
        args = args[1:]
    elif args and args[0] == "--longest-line":
        count = count_longest_line
        args = args[1:]
    if len(args) != 1:
        print(
            f"usage: {argv[0]} [--lines | --bytes | --longest-line] FILE",
            file=sys.stderr,
        )
        return 2
    path = args[0]
    try:
        result = count(path)
    except FileNotFoundError:
        print(f"{argv[0]}: {path}: No such file or directory", file=sys.stderr)
        return 2
    except InvalidUtf8:
        print(f"{argv[0]}: {path}: not valid UTF-8", file=sys.stderr)
        return 2
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
