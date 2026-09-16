#!/usr/bin/env python3
"""What each check of adapter/validation.md decides, asserted directly.

Every test here calls one check and asserts on the Result it returns. Nothing
runs the lint, starts a process or reaches a network, so the whole file is a
fraction of a second and can be run on every edit. `selftest-lint.py` is the
other half: it runs the whole lint end to end and proves the report renders and
the exit status is right, which is what these cannot see.

**These read as a second statement of the contract, and that is deliberate.**
Prose restating the Turtle is forbidden here because it can disagree in silence;
a test restating it cannot, because disagreement fails the build. So a test's
name is a sentence -- `it_blames_the_crate_when...` -- and the assertion is the
documentation. Comments are for what a reader could not infer.

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

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bridgelint import crate as crate_module  # noqa: E402
from bridgelint.checks import (  # noqa: E402
    digests,
    graphs,
    inputs,
    inventory,
    queries,
    shapes,
    specpin,
)
from bridgelint.result import FAIL, NONE, NOT_RUN, OK  # noqa: E402
from bridgelint.terms import BRIDGE, SCHEMA  # noqa: E402
from rdflib import Graph, Literal, URIRef  # noqa: E402

PACKAGE = Path(__file__).resolve().parent.parent / "fixtures" / "synthetic-adapter"

CRATE = "ro-crate-metadata.json"
INPUT_SET = "fixtures/in/example-0001.xml"
EXPECTED = "fixtures/expected/example-0001.ttl"
DETECT_QUERY = "in/example-detect.rq"
FINDINGS_QUERY = "in/example-findings.rq"
MAPPING = "in/example-record.rq"


# ---------------------------------------------------------------------------
# A package to break, and the loaded crate for it
# ---------------------------------------------------------------------------


class Package:
    """A copy of the fixture package that a test may break.

    One of these is shared by the whole run, because parsing the crate is the
    expensive thing here and every test would otherwise pay for it. What keeps
    that safe is `restore`: a test declares the files it breaks by breaking them
    through `edit` and `write`, and they are put back before the next one. The
    graph is never shared -- `crate` hands out a copy, so a test that mutates
    triples cannot reach another.
    """

    def __init__(self, directory, name="package"):
        self.path = Path(directory) / name
        shutil.copytree(PACKAGE, self.path)
        self.tracked = False
        self.broken = set()
        self._base = None
        self.loose = None

    def restore(self):
        """Put back every file a test broke, and forget the graph it mutated."""
        for relative in sorted(self.broken):
            source = PACKAGE / relative
            target = self.path / relative
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
        assert text.count(old) == 1, f"{relative}: {old!r} occurs {text.count(old)} times"
        self.broken.add(relative)
        path.write_text(text.replace(old, new), encoding="utf-8", newline="")
        return self

    def write(self, relative, text):
        self.broken.add(relative)
        (self.path / relative).write_text(text, encoding="utf-8", newline="")
        return self._git_add()

    @property
    def crate(self):
        """The crate, with a graph of its own.

        The parse happens once for the whole run: it is the slow part, and no
        test changes the crate or the manifest on disk -- a test that wants a
        different crate says so in triples, on the copy it is given here.
        """
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

    def entity(self, crate, relative):
        """The crate entity for a file in the package, by IRI."""
        return URIRef((self.path / relative).resolve().as_uri())


def said(result):
    """Everything the result would print, as one string."""
    return "\n".join(
        entry.text + "\n" + "\n".join(entry.detail) for entry in result.entries
    )


# ===========================================================================
# Check 3: every git-tracked file is accounted for
# ===========================================================================


def it_passes_when_every_tracked_file_is_described_or_allowlisted(pkg):
    result = inventory.run(pkg.git_init().crate)
    assert result.status == OK
    assert not result.fails


def it_fails_a_tracked_file_the_crate_describes_nowhere(pkg):
    pkg.git_init()
    pkg.write("fixtures/in/undescribed.xml", "<ExampleRecord/>")
    result = inventory.run(pkg.crate)
    assert result.status == FAIL
    assert "undescribed.xml" in said(result)
    assert "no crate entity with a declared encodingFormat" in said(result)


def it_allowlists_the_four_repository_documents_and_dotfiles(pkg):
    pkg.git_init()
    pkg.write("README.md", "# nothing the crate describes")
    pkg.write(".editorconfig", "root = true")
    result = inventory.run(pkg.crate)
    assert result.status == OK, "a README and a dotfile describe the repository"


def it_refuses_to_take_an_inventory_of_what_is_not_a_git_checkout(pkg):
    result = inventory.run(pkg.loose.crate)
    assert result.status == NOT_RUN
    assert result.fails, "a check that could not run has not passed"


# ===========================================================================
# Check 2: the crate and the test manifest conform to the shapes
# ===========================================================================


def it_passes_a_crate_and_manifest_that_conform(pkg):
    result = shapes.run(pkg.crate)
    assert result.status == OK


def it_fails_a_crate_that_names_no_mapping(pkg):
    crate = pkg.crate
    crate.graph.remove((crate.root, BRIDGE.mapping, None))
    result = shapes.run(crate)
    assert result.status == FAIL
    assert "names at least one bridge:mapping" in said(result)


def it_fails_a_crate_that_does_not_require_sparql_1_1(pkg):
    crate = pkg.crate
    crate.graph.remove((crate.root, BRIDGE.profileRequired, None))
    result = shapes.run(crate)
    assert result.status == FAIL
    assert "bridge:sparql-1.1" in said(result)


def it_names_a_missing_spec_pin_in_its_own_words(pkg):
    crate = pkg.crate
    crate.graph.remove((crate.root, BRIDGE.specPin, None))
    result = shapes.run(crate)
    assert result.status == FAIL
    assert result.note == (
        "the crate is valid and the manifest conforms except for the "
        "missing bridge:specPin"
    ), "the one failure every adapter written before this specification will hit"


# ===========================================================================
# Check 4: every digest matches its file
# ===========================================================================


def it_blames_the_crate_when_the_local_sha256_is_not_the_files(pkg):
    crate = pkg.crate
    entity = pkg.entity(crate, INPUT_SET)
    crate.graph.set((entity, SCHEMA.sha256, Literal("0" * 64)))
    result = digests.run(crate)
    assert result.status == FAIL
    assert "the crate's sha256 is not this file's" in said(result)
    assert "it is wrong about the file" in said(result)


def it_blames_this_copy_when_the_publishers_digest_disagrees(pkg):
    crate = pkg.crate
    entity = pkg.entity(crate, "fixtures/in/example-0002.xml")
    md5 = next(p for p in crate.graph.predicates(entity) if str(p).endswith("md5"))
    crate.graph.set((entity, md5, Literal("0" * 32)))
    result = digests.run(crate)
    assert result.status == FAIL
    assert "the publisher's md5 is not this copy's" in said(result)
    assert "A different finding from a wrong sha256" in said(result), (
        "the two claims are different assertions and are reported as such"
    )


def it_records_a_digest_on_bytes_that_are_not_committed_without_comparing_it(pkg):
    result = digests.run(pkg.crate)
    assert result.status == OK
    assert "recorded and not compared" in said(result)
    assert "the lint fetches nothing" in said(result)


# ===========================================================================
# Check 5: every input validates against the declared schema
# ===========================================================================


def it_passes_an_input_that_satisfies_its_envelopes_schema(pkg):
    result = inputs.run(pkg.crate)
    assert result.status == OK
    assert "2 input(s) validated" == result.note


def it_fails_an_input_that_does_not_satisfy_its_schema(pkg):
    pkg.edit(INPUT_SET, 'Version="3"', 'Version="third"')
    result = inputs.run(pkg.crate)
    assert result.status == FAIL
    assert "does not validate against" in said(result)


def it_falls_back_to_the_adapters_source_schema_when_an_envelope_declares_none(pkg):
    crate = pkg.crate
    envelopes = list(crate.graph.objects(crate.root, BRIDGE.envelope))
    without = [
        e for e in envelopes if crate.graph.value(e, BRIDGE.documentSchema) is None
    ]
    assert without, "the fixture carries an envelope declaring no document schema"
    schema, source = inputs.schema_for(crate, without[0])
    assert source == "bridge:sourceSchema"
    assert schema == crate.graph.value(crate.root, BRIDGE.sourceSchema)


def it_says_not_run_rather_than_passed_for_a_schema_language_it_cannot_read(pkg):
    crate = pkg.crate
    schemas = set(crate.graph.objects(crate.root, BRIDGE.sourceSchema)) | set(
        crate.graph.objects(None, BRIDGE.documentSchema)
    )
    for schema in schemas:
        crate.graph.set((schema, SCHEMA.encodingFormat, Literal("application/json")))
    result = inputs.run(crate)
    assert result.status == NOT_RUN
    assert result.benign, "a package outside what the lint reads is not accused"
    assert not result.fails
    assert "outside v1-draft" in said(result)


# ===========================================================================
# Check 6: every expected graph parses
# ===========================================================================


def it_passes_an_expected_graph_that_parses_as_turtle(pkg):
    result = graphs.run(pkg.crate)
    assert result.status == OK


def it_fails_an_expected_graph_that_is_not_turtle(pkg):
    pkg.edit(EXPECTED, "@prefix ex:", "@prefixx ex:")
    result = graphs.run(pkg.crate)
    assert result.status == FAIL
    assert "does not parse as Turtle" in said(result)


def it_never_judges_an_expected_graph_against_cascades_shapes(pkg):
    result = graphs.run(pkg.crate)
    assert "parsed, not judged" in said(result)
    assert "that is a Bridge's validate stage" in said(result)


# ===========================================================================
# Check 7: every query parses in its declared form
# ===========================================================================


def it_passes_queries_that_parse_in_the_form_their_property_declares(pkg):
    result = queries.run(pkg.crate)
    assert result.status == OK
    assert "3 of 3 in their declared form" == result.note


def it_fails_a_mapping_that_is_not_sparql(pkg):
    pkg.edit(MAPPING, "CONSTRUCT", "CONSTRUKT")
    result = queries.run(pkg.crate)
    assert result.status == FAIL
    assert "does not parse as SPARQL 1.1" in said(result)


def it_fails_a_detect_query_that_is_not_an_ask(pkg):
    pkg.edit(DETECT_QUERY, "ASK {", "SELECT * WHERE {")
    result = queries.run(pkg.crate)
    assert result.status == FAIL
    assert "where bridge:detectQuery requires ASK" in said(result)


def it_fails_a_findings_query_that_projects_other_than_the_four_variables(pkg):
    pkg.edit(
        FINDINGS_QUERY,
        "SELECT ?sourceField ?reason ?severity ?context",
        "SELECT ?sourceField ?reason ?severity",
    )
    result = queries.run(pkg.crate)
    assert result.status == FAIL
    assert "?sourceField ?reason ?severity ?context" in said(result)


# ===========================================================================
# The specification pin
# ===========================================================================


def it_reads_the_spec_pin_and_compares_it_with_nothing(pkg):
    result = specpin.run(pkg.crate)
    assert result.status == OK
    assert "read, not compared" in said(result)


def it_fails_a_spec_pin_that_names_no_repository(pkg):
    crate = pkg.crate
    pin = next(crate.graph.objects(crate.root, BRIDGE.specPin))
    crate.graph.remove((pin, SCHEMA.codeRepository, None))
    result = specpin.run(crate)
    assert result.status == FAIL
    assert "does not say which repository holds that commit" in said(result)


# ===========================================================================
# Every check: the four words are four different sentences
# ===========================================================================


def it_never_lets_nothing_to_check_fail_a_run(pkg):
    crate = pkg.crate
    crate.graph.remove((None, BRIDGE.mapping, None))
    crate.graph.remove((None, BRIDGE.findingsQuery, None))
    crate.graph.remove((None, BRIDGE.detectQuery, None))
    result = queries.run(crate)
    assert result.status == NONE
    assert not result.fails, "found nothing of its kind is not a failure"


def it_never_lets_a_check_that_did_not_run_pass_a_run(pkg):
    result = inventory.run(pkg.loose.crate)
    assert result.status == NOT_RUN
    assert result.fails, "a check the lint could not perform is not a pass"


# ---------------------------------------------------------------------------


def sentence(name):
    return name.removeprefix("it_").replace("_", " ")


def tests():
    module = sys.modules[__name__]
    return [
        (name, func)
        for name, func in sorted(vars(module).items(), key=lambda kv: kv[0])
        if name.startswith("it_") and inspect.isfunction(func)
    ]


def index():
    """The spec these tests state, grouped by the section that holds them."""
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
        # A check-3 test needs a package that is not a git checkout at all, and
        # a package cannot be both, so there is a second one for those to ask
        # for by name.
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
