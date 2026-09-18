"""What this repository may name: its own terms, and no repository that consumes it."""

import re
import subprocess
from pathlib import Path

from rdflib import Graph, URIRef

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = "https://ns.cascadeprotocol.org/bridge/v1-draft#"
VOCABULARY = ROOT / "vocab" / "bridge.ttl"

REPOSITORY = re.compile(r"github\.com[/:](?P<owner>[\w.-]+)/(?P<repository>[\w.-]+?)(?:\.git)?(?=[/\s\'\")\]>@]|$)")


def git(*arguments):
    return subprocess.run(["git", *arguments], cwd=ROOT, capture_output=True, encoding="utf-8", check=True).stdout


def own():
    """This repository, from the remote it was cloned from: an adapter and an engine are its siblings."""
    return REPOSITORY.search(git("remote", "get-url", "origin")).group("owner", "repository")


def tracked():
    return [ROOT / name for name in git("ls-files").split("\n") if name]


def test_the_vocabulary_declares_only_its_own_terms():
    graph = Graph().parse(VOCABULARY, format="turtle")
    minted = {
        str(subject)
        for subject in set(graph.subjects())
        if isinstance(subject, URIRef) and str(subject).startswith("https://ns.cascadeprotocol.org/")
    }
    elsewhere = sorted(term for term in minted if not term.startswith(BRIDGE))
    assert elsewhere == [], f"a Cascade term is minted here: {elsewhere}"


def test_no_file_names_a_sibling_repository():
    """An adapter and an engine are this repository's siblings; the tooling takes a directory and names neither."""
    owner, repository = own()
    named = {}
    for path in tracked():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for match in REPOSITORY.finditer(text):
            if match["owner"] == owner and match["repository"] != repository:
                named.setdefault(f"{match['owner']}/{match['repository']}", path.relative_to(ROOT).as_posix())
    assert named == {}, f"sibling repositories named here: {named}"
