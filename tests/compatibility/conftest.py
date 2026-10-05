import json
import os
import shutil
import time

import pytest

from compatibility_world import Api, PullRequests, World, publish_origins


def published_once(root):
    """Every worker of a run copies the one set of origins the first to arrive publishes."""
    commits = root / "commits.json"
    try:
        root.mkdir()
    except FileExistsError:
        deadline = time.monotonic() + 300
        while not commits.is_file():
            assert root.is_dir(), f"the worker publishing the origins in {root} failed"
            assert time.monotonic() < deadline, f"no worker finished publishing the origins in {root}"
            time.sleep(0.1)
        return root / "origins", json.loads(commits.read_text(encoding="utf-8"))
    try:
        written = publish_origins(root / "origins")
    except BaseException:
        shutil.rmtree(root, ignore_errors=True)
        raise
    (root / "commits.tmp").write_text(json.dumps(written), encoding="utf-8")
    os.replace(root / "commits.tmp", commits)
    return root / "origins", written


@pytest.fixture(scope="session")
def published(tmp_path_factory):
    if "PYTEST_XDIST_WORKER" in os.environ:
        return published_once(tmp_path_factory.getbasetemp().parent / "published")
    origins = tmp_path_factory.mktemp("published") / "origins"
    return origins, publish_origins(origins)


@pytest.fixture
def world(tmp_path, published):
    origins, commits = published
    pull_requests = PullRequests()
    api = Api(pull_requests)
    try:
        yield World(tmp_path, origins, commits, pull_requests, api.url)
    finally:
        api.stop()
