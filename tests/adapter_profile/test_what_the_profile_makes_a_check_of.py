import shutil
from pathlib import Path

from rocrate_validator import services

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "adapter"

DISCOVERED = (
    "Every .ttl and .py file under adapter/profile/ whose name does not begin with an underscore is "
    "discovered by rocrate-validator and run over the crate graph of every adapter whose pull request "
    "names this repository. Shapes a Python check applies to some other file belong in shapes/. "
    "A check added or removed on purpose is said here too."
)

CHECKS = {
    "profile/must/adapter.ttl": 30,
    "profile/must/declared_terms.py": 1,
    "profile/must/digests.py": 1,
    "profile/must/envelope.ttl": 4,
    "profile/must/expected_findings.py": 1,
    "profile/must/expected_graphs.py": 1,
    "profile/must/gap_scheme.py": 1,
    "profile/must/inputs.py": 1,
    "profile/must/inventory.py": 1,
    "profile/must/lookups.py": 1,
    "profile/must/media_types.ttl": 2,
    "profile/must/queries.py": 1,
    "profile/must/shapes.py": 1,
    "profile/must/source_accounting.py": 1,
}

A_CONCEPT_MAPS_SHAPES = """@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .

<#Concept> a sh:NodeShape ;
  sh:targetClass skos:Concept ;
  sh:property [ sh:path skos:notation ; sh:minCount 1 ; sh:message "A concept carries a notation." ] .
"""


def discovered(profile):
    checks = {}
    for requirement in services.get_profile("cascade-bridge-adapter", profiles_path=profile).get_requirements():
        named = str(requirement.path.relative_to(profile)).replace("\\", "/")
        checks[named] = checks.get(named, 0) + len(requirement.get_checks())
    return checks


def test_the_profile_makes_a_check_of_these_files_and_of_nothing_else():
    assert discovered(PROFILE) == CHECKS, DISCOVERED


def test_a_shapes_file_dropped_in_must_becomes_a_check_over_every_crate(tmp_path):
    profile = tmp_path / "adapter"
    shutil.copytree(PROFILE, profile)
    (profile / "profile" / "must" / "concept_map.ttl").write_text(A_CONCEPT_MAPS_SHAPES, encoding="utf-8")
    assert discovered(profile) == {**CHECKS, "profile/must/concept_map.ttl": 2}
