import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

CRATE = "ro-crate-metadata.json"
MANIFEST = "fixtures/manifest.ttl"
EXPECTED = "fixtures/expected/example-0001.ttl"


def restate_digest(package, relative):
    """Rewrite the crate's sha256 and contentSize for a file just changed, so a
    case fails for the one reason it names and not also for its digest."""
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


def identifier_not_a_format_id(package):
    package.edit(CRATE, '"identifier": "synthetic-example",', '"identifier": "Synthetic_Example",')


def expected_graph_not_turtle(package):
    package.edit(EXPECTED, "@prefix ex:", "@prefixx ex:")
    restate_digest(package, EXPECTED)


def manifest_not_turtle(package):
    package.edit(MANIFEST, "@prefix mf:", "@prefixx mf:")
    restate_digest(package, MANIFEST)


def no_expected_graphs(package):
    package.edit(
        MANIFEST,
        "<#example-0001> a bridge:IsomorphicConversionTest ;",
        "<#example-0001> a bridge:InputOnlyTest ;",
    )
    package.edit(
        MANIFEST,
        "  ] ;\n  mf:result [\n"
        "    bridge:graph <expected/example-0001.ttl> ;\n"
        "    bridge:findings <findings/example-0001.gaps.json>\n"
        "  ] .",
        "  ] .",
    )
    restate_digest(package, MANIFEST)


def undeclared_context_key(package):
    """JSON-LD expands bridge:specPin from the prefix alone, so only RO-Crate
    1.2's rule that every key is in the @context sees this."""
    package.edit(CRATE, '      "bridge:specPin": "bridge:specPin",\n', "")


def profile_not_an_entity(package):
    package.edit(CRATE, '      "@type": ["CreativeWork", "Profile"],', '      "@type": "CreativeWork",')


def pin_not_a_data_entity(package):
    package.edit(
        CRATE,
        '      "@type": ["SoftwareSourceCode", "File"],\n'
        '      "name": "cascade-bridge-spec at 0af0fc9",',
        '      "@type": "SoftwareSourceCode",\n'
        '      "name": "cascade-bridge-spec at 0af0fc9",',
    )


@pytest.mark.parametrize(
    "mutate, passes, says, never_says",
    [
        pytest.param(None, True, [], [], id="the fixture package as committed passes"),
        pytest.param(
            identifier_not_a_format_id, False,
            ["The adapter carries exactly one identifier, the format id"], [],
            id="a shape unmet fails: an identifier that is not a format id",
        ),
        pytest.param(
            expected_graph_not_turtle, False,
            ["example-0001: example-0001.ttl does not parse as Turtle"],
            ["sha256 is not this file's"],
            id="a requirement unmet fails: an expected graph that is not Turtle",
        ),
        pytest.param(
            manifest_not_turtle, False, ["could not be checked", "manifest.ttl"], [],
            id="a requirement that could not run fails: a manifest that is not Turtle",
        ),
        pytest.param(
            no_expected_graphs, True, [], [],
            id="nothing of its kind passes: no expected graphs",
        ),
        pytest.param(
            undeclared_context_key, False,
            ["is not allowed in the compacted format because it is not present in the @context"], [],
            id="RO-Crate 1.2 is inherited: a key the @context does not declare",
        ),
        pytest.param(
            profile_not_an_entity, False, ["MUST reference Profile entities"], [],
            id="RO-Crate 1.2 is inherited: what conformsTo names is not typed Profile",
        ),
        pytest.param(
            pin_not_a_data_entity, False, ["MUST include `File` in its `@type`"], [],
            id="RO-Crate 1.2 is inherited: a pin typed SoftwareSourceCode and not File",
        ),
    ],
)
def test_the_validator_runs_the_profile(package, tmp_path, mutate, passes, says, never_says):
    if mutate:
        mutate(package)
    report = tmp_path / "report.json"
    run = subprocess.run(
        [
            "rocrate-validator", "validate", str(package.path),
            "--extra-profiles-path", str(ROOT / "adapter"),
            "--profile-identifier", "cascade-bridge-adapter",
            "--no-paging", "--output-format", "json", "--output-file", str(report),
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        # The validator logs through rich, which a Windows console code page
        # cannot encode.
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert report.is_file(), run.stdout + run.stderr
    found = json.loads(report.read_text(encoding="utf-8"))
    issues = "\n".join(str(issue["message"]) for issue in found["issues"])

    assert found["passed"] is passes, issues
    assert run.returncode == (0 if passes else 1), issues
    for fragment in says:
        assert fragment in issues
    for fragment in never_says:
        assert fragment not in issues
