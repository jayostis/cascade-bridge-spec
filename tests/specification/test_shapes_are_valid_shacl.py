from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph

ROOT = Path(__file__).resolve().parents[2]
SHAPES_FILES = [
    *sorted((ROOT / "shapes").glob("*.ttl")),
    *sorted((ROOT / "adapter" / "profile" / "must").glob("*.ttl")),
    *sorted((ROOT / "fixtures" / "synthetic-vocabularies").rglob("*.shapes.ttl")),
]


@pytest.mark.parametrize("shapes_file", SHAPES_FILES, ids=lambda path: path.relative_to(ROOT).as_posix())
def test_every_shapes_file_is_valid_shacl(shapes_file):
    shapes = Graph().parse(shapes_file, format="turtle")
    conforms, _, text = validate(shapes, shacl_graph=shapes, meta_shacl=True)
    assert conforms, text
