import hashlib
import re

import pytest
from rocrate_validator import services
from rocrate_validator.models import ValidationSettings

from adapter_profile_world import FIXTURE, ROOT

PROFILES = ROOT / "adapter"
PROFILE = "cascade-bridge-adapter"
INHERITED = "ro-crate-1.2"
SYNTHETIC_ADAPTER = FIXTURE

CRATE = "ro-crate-metadata.json"
MANIFEST = "fixtures/manifest.ttl"


def restate_digest(package, relative):
    data = (package.path / relative).read_bytes()
    crate = package.path / CRATE
    text = crate.read_text(encoding="utf-8")
    start = text.index(f'"@id": "{relative}",')
    end = text.index("\n    }", start)
    entity = re.sub(
        r'"sha256": "[0-9a-f]{64}"',
        f'"sha256": "{hashlib.sha256(data).hexdigest()}"',
        text[start:end],
    )
    entity = re.sub(r'"contentSize": "\d+"', f'"contentSize": "{len(data)}"', entity)
    crate.write_text(text[:start] + entity + text[end:], encoding="utf-8", newline="")


def validated(adapter):
    return services.validate(
        ValidationSettings(rocrate_uri=str(adapter), extra_profiles_path=PROFILES, profile_identifier=PROFILE)
    )


def files_of(checks):
    return {check.requirement.path.resolve() for check in checks if check.requirement.path}


@pytest.fixture(scope="module")
def the_committed_fixture():
    return validated(SYNTHETIC_ADAPTER)


def test_the_committed_synthetic_adapter_passes_the_profile(the_committed_fixture):
    assert the_committed_fixture.passed(), "\n".join(issue.message for issue in the_committed_fixture.get_issues())


def test_every_file_the_profile_makes_a_check_of_is_run(the_committed_fixture):
    requirements = services.get_profile(PROFILE, profiles_path=PROFILES).get_requirements()
    declared = files_of(check for requirement in requirements for check in requirement.get_checks())
    assert len(declared) > 1
    assert declared <= files_of(the_committed_fixture.executed_checks)
    assert not the_committed_fixture.skipped_checks


def test_the_checks_of_ro_crate_1_2_are_inherited(the_committed_fixture):
    assert any(check.requirement.profile.identifier == INHERITED for check in the_committed_fixture.executed_checks)


def test_a_check_that_could_not_run_fails_the_profile_naming_why(tracked_package):
    tracked_package.edit(MANIFEST, "@prefix mf:", "@prefixx mf:")
    restate_digest(tracked_package, MANIFEST)

    result = validated(tracked_package.path)

    said = "\n".join(issue.message for issue in result.get_issues())
    assert not result.passed()
    assert "could not be checked" in said
    assert "manifest.ttl" in said
