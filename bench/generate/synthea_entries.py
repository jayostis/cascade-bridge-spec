"""python3 bench/generate/synthea_entries.py <synthea output folder>"""

import argparse
import json
import sys
from pathlib import Path

NOT_A_PERSON = ("hospitalInformation", "practitionerInformation")


def entries_per_person(folder):
    counts = {}
    for path in sorted((folder / "fhir").glob("*.json")):
        if path.name.startswith(NOT_A_PERSON):
            continue
        name, _, person = path.stem.rpartition("_")
        counts[person] = (name, len(json.loads(path.read_text(encoding="utf-8"))["entry"]), path.stat().st_size)
    return counts


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    arguments = parser.parse_args(argv)
    print("entries bytes person name")
    for person, (name, entries, size) in sorted(entries_per_person(arguments.folder).items(), key=lambda p: p[1][1]):
        print(entries, size, person, name)


if __name__ == "__main__":
    main(sys.argv[1:])
