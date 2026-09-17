from enum import Enum


class Stop(Exception):
    pass


class Status(Enum):
    OK = ("ok", "PASS", 0)
    FAIL = ("FAIL", "FAIL", 1)
    NOTHING_TO_CHECK = ("nothing to check", "nothing to check", 0)

    def __init__(self, word, verdict, exit_code):
        self.word = word
        self.verdict = verdict
        self.exit_code = exit_code


def report(ok, line):
    print(("  ok    " if ok else "  FAIL  ") + line)


def note(line):
    print("  note  " + line)


def warn(line):
    print("  warn  " + line)


def detail(line):
    print("        " + line)


def first_line(text):
    return next((line.strip() for line in text.splitlines() if line.strip()), "")
