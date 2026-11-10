import subprocess
from pathlib import Path

import pytest
from rdflib import Graph

ROOT = Path(__file__).resolve().parents[2]
FORMATS = {".ttl": "turtle", ".nt": "nt"}


def tracked(*patterns):
    run = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", *patterns], capture_output=True, encoding="utf-8", check=True
    )
    return sorted(path for path in run.stdout.split("\0") if path)


class TestFilesOfTheSpecificationThatParse:
    """Files of the specification that parse · **/*.ttl, **/*.nt, shapes/, bench/result.schema.json"""

    class TestGivenATrackedTurtleOrNTriplesFile:
        """given a tracked Turtle or N-Triples file"""

        @pytest.mark.parametrize("path", tracked("*.ttl", "*.nt"))
        def test_parses(self, path):
            file = ROOT / path
            Graph().parse(file, format=FORMATS[file.suffix], publicID=file.as_uri())
