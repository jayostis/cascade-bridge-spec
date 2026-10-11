"""python3 bench/generate/repeat_entries.py <in.xml> <factor> <out[.gz]>"""

import argparse
import gzip
import hashlib
import re
import sys
from pathlib import Path

ENTRY = re.compile(r"<entry[ >][\s\S]*?</entry>")
ID = re.compile(r'(<id root="[^"]*")( extension="[^"]*")?')


def repeat_entries(document, factor):
    counter = 0

    def renumbered(match, copy):
        nonlocal counter
        extension = f'{match.group(1)} extension="gen-{copy}-{counter}"'
        counter += 1
        return extension

    def repeated(entry):
        return "".join(
            ID.sub(lambda match, copy=copy: renumbered(match, copy), entry.group(0)) + "\n" for copy in range(factor)
        )

    return ENTRY.sub(repeated, document)


def digest_line(label, data):
    return f"{label} sha256 {hashlib.sha256(data).hexdigest()} bytes {len(data)}"


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("factor", type=int)
    parser.add_argument("out", type=Path)
    arguments = parser.parse_args(argv)
    if arguments.factor < 1:
        parser.error("factor is at least 1")

    with open(arguments.source, encoding="utf-8", newline="") as handle:
        document = repeat_entries(handle.read(), arguments.factor).encode("utf-8")
    written = gzip.compress(document, compresslevel=9, mtime=0) if arguments.out.suffix == ".gz" else document
    arguments.out.write_bytes(written)
    print(digest_line("document", document))
    print(digest_line("file", written))


if __name__ == "__main__":
    main(sys.argv[1:])
