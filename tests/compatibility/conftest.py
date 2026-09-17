import pytest

from compatibility_world import World, publish_origins


@pytest.fixture(scope="session")
def published(tmp_path_factory):
    origins = tmp_path_factory.mktemp("published") / "origins"
    return origins, publish_origins(origins)


@pytest.fixture
def world(tmp_path, published):
    origins, commits = published
    return World(tmp_path, origins, commits)
