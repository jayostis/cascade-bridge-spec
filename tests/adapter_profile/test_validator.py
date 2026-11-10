import hashlib
import re

import pytest
from rocrate_validator import services
from rocrate_validator.models import Severity, ValidationSettings

from adapter_profile_world import FIXTURE, JSON_FIXTURE, ROOT

PROFILES = ROOT / "adapter"
PROFILE = "cascade-bridge-adapter"
INHERITED = "ro-crate-1.2"
SYNTHETIC_ADAPTER = FIXTURE

CRATE = "ro-crate-metadata.json"
MANIFEST = "fixtures/manifest.ttl"
ACCOUNTING = "vocab/example-accounting.ttl"
VALIDATED_ONCE = pytest.mark.xdist_group("the committed synthetic adapter, validated once")


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


class TestCheckingAnAdapterPackageAgainstTheProfile:
    """Checking an adapter package against the profile · rocrate-validator, adapter/profile/must/

    An adapter package conforms when `rocrate-validator` passes it against RO-Crate 1.2 and this profile. Each `.ttl` or
    `.py` file under `adapter/profile/must/` is one requirement, and a requirement that could not be checked fails the
    package and says why.
    """

    class TestGivenTheSyntheticAdaptersAsCommitted:
        @VALIDATED_ONCE
        def test_passes_the_xml_adapter(self, the_committed_fixture):
            """passes the XML adapter"""
            assert the_committed_fixture.passed(), "\n".join(
                issue.message for issue in the_committed_fixture.get_issues()
            )

        def test_passes_the_json_adapter(self):
            """passes the JSON adapter"""
            result = validated(JSON_FIXTURE)
            assert result.passed(), "\n".join(issue.message for issue in result.get_issues())

        @VALIDATED_ONCE
        def test_runs_every_file_the_profile_makes_a_check_of_skipping_none(self, the_committed_fixture):
            """runs every file the profile makes a check of, skipping none"""
            requirements = services.get_profile(PROFILE, profiles_path=PROFILES).get_requirements()
            declared = files_of(check for requirement in requirements for check in requirement.get_checks())
            assert len(declared) > 1
            assert declared <= files_of(the_committed_fixture.executed_checks)
            assert not the_committed_fixture.skipped_checks

        @VALIDATED_ONCE
        def test_runs_the_checks_of_ro_crate_1_2_as_well(self, the_committed_fixture):
            """runs the checks of RO-Crate 1.2 as well"""
            assert any(
                check.requirement.profile.identifier == INHERITED for check in the_committed_fixture.executed_checks
            )

    class TestGivenAPackageAtFault:
        def test_fails_one_whose_carried_entry_names_no_term_as_a_required_issue(self, tracked_package):
            """fails one whose carried entry names no term, as a required issue"""
            tracked_package.edit(
                ACCOUNTING,
                " ;\n  bridge:carriedAs [ bridge:asProperty ex:accession ; bridge:inRecordClass ex:Record ] .",
                " .",
            )
            restate_digest(tracked_package, ACCOUNTING)

            result = validated(tracked_package.path)

            failed = [issue for issue in result.get_issues() if "names at least one bridge:carriedAs" in issue.message]
            assert not result.passed()
            assert {issue.severity for issue in failed} == {Severity.REQUIRED}

        def test_fails_one_whose_check_could_not_run_naming_why_and_the_file(self, tracked_package):
            """fails one whose check could not run, naming why and the file"""
            tracked_package.edit(MANIFEST, "@prefix mf:", "@prefixx mf:")
            restate_digest(tracked_package, MANIFEST)

            result = validated(tracked_package.path)

            said = "\n".join(issue.message for issue in result.get_issues())
            assert not result.passed()
            assert "could not be checked" in said
            assert "manifest.ttl" in said
