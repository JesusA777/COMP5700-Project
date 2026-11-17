"""Runs Task 1 -> 2 -> 3 for two PDFs. Owner: Person C (integration)."""

import sys


def main(argv):
    if len(argv) != 2:
        print("Usage: main <first.pdf> <second.pdf>")
        return 1
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
