#!/usr/bin/env python3
"""What each requirement of the cascade-bridge-adapter profile decides.

Every requirement under scripts/profiles/cascade-bridge-adapter/must/ is a plain
generator of the messages it would report, and a four-line class that hands them
to the validator. These tests call the generator. Nothing runs the lint, starts a
process or reaches a network, so the file is seconds and can be run on every
edit; selftest-lint.py is the other half, and runs the whole thing.

**These read as a second statement of the contract, and that is deliberate.**
Prose restating the Turtle is forbidden here because it can disagree in silence;
a test restating it cannot, because disagreement fails the build. So a test's
name is the sentence it asserts, and the assertion is the documentation.

Run:  python3 scripts/unittest-lint.py            every test
      python3 scripts/unittest-lint.py digests    the ones whose name holds it
      python3 scripts/unittest-lint.py --index    emit the spec they state
"""

from __future__ import annotations

import inspect
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "profiles" / "cascade-bridge-adapter" / "must"))

import digests  # noqa: E402
import expected_graphs  # noqa: E402
import inputs  # noqa: E402
import inventory  # noqa: E402
import queries  # noqa: E402
import shapes  # noqa: E402
import spec_pin  # noqa: E402
from bridgelint import crate as crate_module  # noqa: E402
from bridgelint.terms import BRIDGE, SCHEMA  # noqa: E402
from rdflib import Graph, Literal, URIRef  # noqa: E402

PACKAGE = HERE.parent / "fixtures" / "synthetic-adapter"

INPUT_SET = "fixtures/in/example-0001.xml"
INPUT_RECORD = "fixtures/in/example-0002.xml"
EXPECTED = "fixtures/expected/example-0001.ttl"
DETECT_QUERY = "in/example-detect.rq"
FINDINGS_QUERY = "in/example-findings.rq"
MAPPING = "in/example-record.rq"


class Package:
    """A copy of the fixture package that a test may break.

    One is shared by the whole run, because parsing the crate is the expensive
    thing here and every test would otherwise pay for it. `restore` puts back
    what a test broke through `edit` or `write`. The graph is never shared:
    `crate` hands out a copy, so a test that mutates triples cannot reach
    another.
    """

    def __init__(self, directory, name="package"):
        self.path = Path(directory) / name
        shutil.copytree(PACKAGE, self.path)
        self.tracked = False
        self.broken = set()
        self._base = None
        self.loose = None

    def restore(self):
        for relative in sorted(self.broken):
            source, target = PACKAGE / relative, self.path / relative
            if source.is_file():
                shutil.copyfile(source, target)
            elif target.exists():
                target.unlink()
        if self.broken:
            self.broken.clear()
            self._git_add()
        return self

    def git_init(self):
        subprocess.run(
            ["git", "init", "-q", str(self.path)], check=True, capture_output=True
        )
        self.tracked = True
        return self._git_add()

    def _git_add(self):
        if self.tracked:
            subprocess.run(
                ["git", "-C", str(self.path), "add", "-A"],
                check=True,
                capture_output=True,
            )
        return self

    def edit(self, relative, old, new):
        path = self.path / relative
        text = path.read_text(encoding="utf-8")
        assert text.count(old) == 1, f"{relative}: {old!r} occurs {text.count(old)}x"
        self.broken.add(relative)
        path.write_text(text.replace(old, new), encoding="utf-8", newline="")
        return self

    def write(self, relative, text):
        self.broken.add(relative)
        (self.path / relative).write_text(text, encoding="utf-8", newline="")
        return self._git_add()

    @property
    def crate(self):
        if self._base is None:
            self._base = crate_module.load(self.path)
        graph = Graph()
        for triple in self._base.graph:
            graph.add(triple)
        return crate_module.Crate(
            self._base.adapter,
            graph,
            self._base.root,
            self._base.manifest_iri,
            self._base.manifest_file,
        )

    def entity(self, relative):
        return URIRef((self.path / relative).resolve().as_uri())


def said(messages):
    return "\n".join(messages)


# ===========================================================================
# The crate and the test manifest conform to the shapes
# ===========================================================================


def it_reports_nothing_for_a_crate_and_manifest_that_conform(pkg):
    assert not list(shapes.violations(pkg.crate))


def it_reports_a_crate_that_names_no_mapping(pkg):
    crate = pkg.crate
    crate.graph.remove((crate.root, BRIDGE.mapping, None))
    assert "names at least one bridge:mapping" in said(shapes.violations(crate))


def it_reports_a_crate_that_does_not_require_sparql_1_1(pkg):
    crate = pkg.crate
    crate.graph.remove((crate.root, BRIDGE.profileRequired, None))
    assert "bridge:sparql-1.1" in said(shapes.violations(crate))


def it_reports_a_missing_spec_pin_by_naming_the_term(pkg):
    crate = pkg.crate
    crate.graph.remove((crate.root, BRIDGE.specPin, None))
    assert "bridge:specPin" in said(shapes.violations(crate)), (
        "the one failure every adapter written before this specification will "
        "hit, and a generic message would send its author to the wrong file"
    )


# ===========================================================================
# Every git-tracked file is accounted for
# ===========================================================================


def it_reports_nothing_when_every_tracked_file_is_described_or_allowlisted(pkg):
    assert not list(inventory.unaccounted(pkg.git_init().crate))


def it_reports_a_tracked_file_the_crate_describes_nowhere(pkg):
    pkg.git_init()
    pkg.write("fixtures/in/undescribed.xml", "<ExampleRecord/>")
    found = said(inventory.unaccounted(pkg.crate))
    assert "undescribed.xml" in found
    assert "no crate entity with a declared encodingFormat" in found


def it_allowlists_the_repository_documents_and_dotfiles(pkg):
    pkg.git_init()
    pkg.write("README.md", "# nothing the crate describes")
    pkg.write(".editorconfig", "root = true")
    assert not list(inventory.unaccounted(pkg.crate)), (
        "a README and a dotfile describe the repository, not the package"
    )


def it_reports_a_package_that_is_not_a_git_checkout(pkg):
    found = said(inventory.unaccounted(pkg.loose.crate))
    assert "is not a git checkout" in found, (
        "a requirement nothing could check must not pass in silence"
    )


# ===========================================================================
# Every digest matches its file
# ===========================================================================


def it_blames_the_crate_when_the_local_sha256_is_not_the_files(pkg):
    crate = pkg.crate
    crate.graph.set((pkg.entity(INPUT_SET), SCHEMA.sha256, Literal("0" * 64)))
    found = said(digests.mismatches(crate))
    assert "the crate's sha256 is not this file's" in found
    assert "it is wrong about the file beside it" in found


def it_blames_this_copy_when_the_publishers_digest_disagrees(pkg):
    crate = pkg.crate
    entity = pkg.entity(INPUT_RECORD)
    md5 = next(p for p in crate.graph.predicates(entity) if str(p).endswith("md5"))
    crate.graph.set((entity, md5, Literal("0" * 32)))
    found = said(digests.mismatches(crate))
    assert "the publisher's md5 is not this copy's" in found
    assert "A different finding from a wrong sha256" in found, (
        "the two claims are different assertions and are reported as such"
    )


def it_never_compares_a_digest_on_bytes_that_are_not_committed(pkg):
    crate = pkg.crate
    committed = {path for path, _, _, _ in digests.claims(crate)}
    assert committed, "the fixture records digests on committed files"
    assert all(path.is_file() for path in committed), (
        "a digest on a referenced release is recorded and not compared, which "
        "is why nothing is fetched"
    )


# ===========================================================================
# Every input validates against the declared schema
# ===========================================================================


def it_reports_nothing_for_an_input_that_satisfies_its_envelopes_schema(pkg):
    assert not list(inputs.invalid(pkg.crate))


def it_reports_an_input_that_does_not_satisfy_its_schema(pkg):
    pkg.edit(INPUT_SET, 'Version="3"', 'Version="third"')
    assert "does not validate against" in said(inputs.invalid(pkg.crate))


def it_falls_back_to_the_adapters_source_schema_when_an_envelope_declares_none(pkg):
    crate = pkg.crate
    without = [
        e
        for e in crate.graph.objects(crate.root, BRIDGE.envelope)
        if crate.graph.value(e, BRIDGE.documentSchema) is None
    ]
    assert without, "the fixture carries an envelope declaring no document schema"
    schema, declared_by = inputs.schema_for(crate, without[0])
    assert declared_by == "bridge:sourceSchema"
    assert schema == crate.graph.value(crate.root, BRIDGE.sourceSchema)


def it_holds_a_package_to_nothing_when_the_schema_language_is_one_it_cannot_read(pkg):
    crate = pkg.crate
    schemas = set(crate.graph.objects(crate.root, BRIDGE.sourceSchema)) | set(
        crate.graph.objects(None, BRIDGE.documentSchema)
    )
    for schema in schemas:
        crate.graph.set((schema, SCHEMA.encodingFormat, Literal("application/json")))
    assert not list(inputs.invalid(crate)), (
        "a JSON source schema is outside v1-draft: a gap in this lint, not a "
        "fault in the package"
    )


# ===========================================================================
# Every expected graph parses as Turtle
# ===========================================================================


def it_reports_nothing_for_an_expected_graph_that_parses(pkg):
    assert not list(expected_graphs.unparsable(pkg.crate))


def it_reports_an_expected_graph_that_is_not_turtle(pkg):
    pkg.edit(EXPECTED, "@prefix ex:", "@prefixx ex:")
    assert "does not parse as Turtle" in said(expected_graphs.unparsable(pkg.crate))


def it_never_judges_an_expected_graph_against_cascades_shapes(pkg):
    pkg.edit(
        EXPECTED,
        "@prefix ex:   <https://example.org/synthetic-adapter/v1#> .",
        "@prefix ex:   <https://example.org/synthetic-adapter/v1#> .\n"
        "<https://example.org/x> <https://example.org/undefined> 1 .",
    )
    assert not list(expected_graphs.unparsable(pkg.crate)), (
        "a term no vocabulary defines is a Bridge's validate stage to judge, "
        "and parsing is all this asks"
    )


# ===========================================================================
# Every query parses in its declared form
# ===========================================================================


def it_reports_nothing_for_queries_in_the_form_their_property_declares(pkg):
    assert not list(queries.malformed(pkg.crate))


def it_reports_a_mapping_that_is_not_sparql(pkg):
    pkg.edit(MAPPING, "CONSTRUCT", "CONSTRUKT")
    assert "does not parse as SPARQL 1.1" in said(queries.malformed(pkg.crate))


def it_reports_a_detect_query_that_is_not_an_ask(pkg):
    pkg.edit(DETECT_QUERY, "ASK {", "SELECT * WHERE {")
    assert "where bridge:detectQuery requires ASK" in said(
        queries.malformed(pkg.crate)
    )


def it_reports_a_findings_query_projecting_other_than_the_four_variables(pkg):
    pkg.edit(
        FINDINGS_QUERY,
        "SELECT ?sourceField ?reason ?severity ?context",
        "SELECT ?sourceField ?reason ?severity",
    )
    assert "?sourceField ?reason ?severity ?context" in said(
        queries.malformed(pkg.crate)
    )


def it_reports_nothing_when_the_adapter_names_no_query(pkg):
    crate = pkg.crate
    for term in (BRIDGE.mapping, BRIDGE.findingsQuery, BRIDGE.detectQuery):
        crate.graph.remove((crate.root, term, None))
    assert not list(queries.malformed(crate)), (
        "found nothing of its kind is not a fault: the shapes are what require "
        "an adapter to name a mapping at all"
    )


# ===========================================================================
# The specification pin
# ===========================================================================


def it_reports_nothing_for_a_pin_naming_a_commit_and_its_repository(pkg):
    assert not list(spec_pin.faults(pkg.crate))


def it_reports_a_spec_pin_that_names_no_repository(pkg):
    crate = pkg.crate
    pin = next(crate.graph.objects(crate.root, BRIDGE.specPin))
    crate.graph.remove((pin, SCHEMA.codeRepository, None))
    assert "does not say which repository holds that commit" in said(
        spec_pin.faults(crate)
    )


# ---------------------------------------------------------------------------


def sentence(name):
    return name.removeprefix("it_").replace("_", " ")


def tests():
    module = sys.modules[__name__]
    return [
        (name, func)
        for name, func in sorted(vars(module).items())
        if name.startswith("it_") and inspect.isfunction(func)
    ]


def index():
    """The spec these tests state, grouped by the requirement they are about."""
    source = Path(__file__).read_text(encoding="utf-8").splitlines()
    heading = None
    print("# What the adapter lint decides\n")
    print("Generated by `scripts/unittest-lint.py --index`. Do not edit.\n")
    for number, line in enumerate(source):
        if line.startswith("# ") and number and source[number - 1].startswith("# ==="):
            heading = line[2:].strip()
        found = re.match(r"^def (it_\w+)\(", line)
        if found:
            if heading:
                print(f"\n## {heading}\n")
                heading = None
            print(f"- It {sentence(found.group(1))}.")


def main(argv):
    if "--index" in argv:
        index()
        return 0

    chosen = [
        (name, func)
        for name, func in tests()
        if all(term.lower() in name.lower() for term in argv)
    ]
    if not chosen:
        raise SystemExit(f"  FAIL  no test matches {' '.join(argv)}")

    failed = 0
    with tempfile.TemporaryDirectory() as directory:
        shared = Package(directory).git_init()
        # One test needs a package that is not a git checkout at all, and a
        # package cannot be both.
        shared.loose = Package(directory, "loose")
        for name, func in chosen:
            try:
                func(shared)
            except AssertionError as error:
                failed += 1
                print(f"  FAIL  it {sentence(name)}")
                print(f"        {error}")
                continue
            finally:
                shared.restore()
                shared.loose.restore()
            print(f"  ok    it {sentence(name)}")

    print()
    print(f"{len(chosen)} test(s): {len(chosen) - failed} as specified, {failed} not")
    if len(chosen) != len(tests()):
        print(f"{len(tests()) - len(chosen)} not run: this is a filtered run")
    print("PASS" if not failed else "FAIL")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
