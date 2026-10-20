"""Count whitespace-separated words in a file."""

import sys


def count_words(path):
    with open(path, encoding="utf-8") as handle:
        return len(handle.read().split())


def main(argv):
    if len(argv) != 2:
        print(f"usage: {argv[0]} FILE", file=sys.stderr)
        return 2
    path = argv[1]
    try:
        count = count_words(path)
    except FileNotFoundError:
        print(f"{argv[0]}: {path}: No such file or directory", file=sys.stderr)
        return 2
    print(count)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
