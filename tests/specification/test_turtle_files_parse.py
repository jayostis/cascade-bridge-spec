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


def test_there_are_turtle_files_to_parse():
    assert tracked("*.ttl") and tracked("*.nt")


@pytest.mark.parametrize("path", tracked("*.ttl", "*.nt"))
def test_every_tracked_turtle_and_n_triples_file_parses(path):
    file = ROOT / path
    Graph().parse(file, format=FORMATS[file.suffix], publicID=file.as_uri())
