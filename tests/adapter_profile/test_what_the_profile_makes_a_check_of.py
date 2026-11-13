import shutil

from rocrate_validator import services

from adapter_profile_world import ROOT

PROFILE = ROOT / "adapter"

DISCOVERED = (
    "Every .ttl and .py file under adapter/profile/ other than the profile.ttl descriptor, and whose name "
    "does not begin with an underscore, is discovered by rocrate-validator and run over the crate graph of "
    "every adapter whose pull request names this repository. Shapes a Python check applies to some other "
    "file belong in shapes/. A check added or removed on purpose is said here too."
)

CHECKS = {
    "profile/must/adapter.ttl": 35,
    "profile/must/bench_inputs.py": 1,
    "profile/must/carried_as.py": 1,
    "profile/must/declared_terms.py": 1,
    "profile/must/digests.py": 1,
    "profile/must/envelope.ttl": 12,
    "profile/must/expected_findings.py": 1,
    "profile/must/expected_graphs.py": 1,
    "profile/must/facts.py": 1,
    "profile/must/gap_scheme.py": 1,
    "profile/must/inputs.py": 1,
    "profile/must/inventory.py": 1,
    "profile/must/lookups.py": 1,
    "profile/must/media_types.ttl": 2,
    "profile/must/queries.py": 1,
    "profile/must/record_type_names.py": 1,
    "profile/must/schema_imports.py": 1,
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


class TestCheckingAnAdapterPackageAgainstTheProfile:
    """Checking an adapter package against the profile · rocrate-validator, adapter/profile/must/

    An adapter package conforms when `rocrate-validator` passes it against RO-Crate 1.2 and this profile. Each `.ttl` or
    `.py` file under `adapter/profile/must/` is one requirement, and a requirement that could not be checked fails the
    package and says why.
    """

    class TestGivenTheFilesUnderAdapterProfile:
        """given the files under `adapter/profile/`"""

        def test_makes_a_check_of_each_ttl_and_py_under_must_and_of_nothing_else(self):
            """makes a check of each `.ttl` and `.py` under `must/`, and of nothing else"""
            assert discovered(PROFILE) == CHECKS, DISCOVERED

        def test_makes_a_shapes_file_dropped_into_must_a_check_over_every_crate(self, tmp_path):
            """makes a shapes file dropped into `must/` a check over every crate"""
            profile = tmp_path / "adapter"
            shutil.copytree(PROFILE, profile)
            (profile / "profile" / "must" / "concept_map.ttl").write_text(A_CONCEPT_MAPS_SHAPES, encoding="utf-8")
            assert discovered(profile) == {**CHECKS, "profile/must/concept_map.ttl": 2}
