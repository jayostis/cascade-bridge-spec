import dataclasses
import functools
import shutil
import subprocess

import pytest
from rdflib import Graph, URIRef

import _crate
from adapter_profile_world import FIXTURE, JSON_FIXTURE

READ_BY_LOAD = ("ro-crate-metadata.json", "fixtures/manifest.ttl")


@functools.cache
def loaded(fixture):
    """The fixture's crate, read once where it is committed."""
    return _crate.load(fixture), [(fixture / name).read_bytes() for name in READ_BY_LOAD]


def moved(crate, adapter):
    """A crate read from its fixture, as a copy of the fixture at adapter reads, without parsing it again."""
    was, now = crate.adapter.resolve().as_uri(), adapter.resolve().as_uri()

    def move(node):
        return URIRef(now + node[len(was) :]) if isinstance(node, URIRef) and node.startswith(was) else node

    graph = Graph()
    for prefix, namespace in crate.graph.namespaces():
        graph.bind(prefix, namespace, override=True)
    for triple in crate.graph:
        graph.add(tuple(map(move, triple)))
    manifest_iri = move(crate.manifest_iri)
    return _crate.Crate(adapter, graph, move(crate.root), manifest_iri, _crate.path_of(manifest_iri))


class Package:
    def __init__(self, path, tracked=False, fixture=FIXTURE):
        shutil.copytree(fixture, path)
        self.path = path
        self.fixture = fixture
        self.tracked = tracked
        if tracked:
            self._git("init", "-q")
            self._git("add", "-A")

    def _git(self, *args):
        subprocess.run(["git", "-C", str(self.path), *args], check=True, capture_output=True)

    def edit(self, relative, old, new, times=1):
        target = self.path / relative
        text = target.read_text(encoding="utf-8")
        found = text.count(old)
        assert found == times, f"{relative}: {old!r} occurs {found} times, {times} expected"
        target.write_text(text.replace(old, new), encoding="utf-8", newline="")
        return self

    def write(self, relative, text):
        target = self.path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="")
        if self.tracked:
            self._git("add", "-A")
        return self

    @property
    def crate(self):
        committed, read = loaded(self.fixture)
        if [(self.path / name).read_bytes() for name in READ_BY_LOAD] == read:
            return moved(committed, self.path)
        return _crate.load(self.path)


@pytest.fixture
def package(tmp_path):
    return Package(tmp_path / "package")


@pytest.fixture
def tracked_package(tmp_path):
    return Package(tmp_path / "package", tracked=True)


@pytest.fixture(scope="session")
def conforming(tmp_path_factory):
    return Package(tmp_path_factory.mktemp("conforming") / "package", tracked=True).crate


@pytest.fixture
def crate(conforming):
    graph = Graph()
    graph += conforming.graph
    return dataclasses.replace(conforming, graph=graph)


@pytest.fixture
def json_package(tmp_path):
    return Package(tmp_path / "package", fixture=JSON_FIXTURE)


@pytest.fixture(scope="session")
def conforming_json(tmp_path_factory):
    return Package(tmp_path_factory.mktemp("conforming-json") / "package", tracked=True, fixture=JSON_FIXTURE).crate


@pytest.fixture
def json_crate(conforming_json):
    graph = Graph()
    graph += conforming_json.graph
    return dataclasses.replace(conforming_json, graph=graph)
