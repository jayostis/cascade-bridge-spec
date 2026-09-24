import dataclasses
import shutil
import subprocess

import pytest
from rdflib import Graph

import _crate
from adapter_profile_world import FIXTURE


class Package:
    def __init__(self, path, tracked=False):
        shutil.copytree(FIXTURE, path)
        self.path = path
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
