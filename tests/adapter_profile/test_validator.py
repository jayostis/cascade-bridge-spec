import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ROCRATE_VALIDATOR_IN_THIS_PYTHON = [sys.executable, "-c", "from rocrate_validator.cli import cli; cli()"]
UTF8_OUTPUT_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}

CRATE = "ro-crate-metadata.json"
MANIFEST = "fixtures/manifest.ttl"
EXPECTED = "fixtures/expected/example-0001.ttl"
FINDINGS = "fixtures/findings/example-0001.ttl"
ACCOUNTING = "vocab/example-accounting.ttl"


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


def identifier_not_a_format_id(package):
    package.edit(CRATE, '"identifier": "synthetic-example",', '"identifier": "Synthetic_Example",')


def adapter_profile_not_named(package):
    package.edit(
        CRATE,
        '      "conformsTo": [\n'
        "        {\n"
        '          "@id": "https://ns.cascadeprotocol.org/bridge/v1-draft/adapter-profile/"\n'
        "        }\n"
        "      ],\n",
        "",
    )


def expected_graph_not_turtle(package):
    package.edit(EXPECTED, "@prefix ex:", "@prefixx ex:")
    restate_digest(package, EXPECTED)


def a_finding_selecting_no_node(package):
    package.edit(FINDINGS, '"/ExampleRecordSet/ExampleRecord[2]"', '"/ExampleRecordSet/ExampleRecord[3]"', times=2)
    restate_digest(package, FINDINGS)


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
        "    bridge:expectedGraph <expected/example-0001.ttl> ;\n"
        "    bridge:expectedFindings <findings/example-0001.ttl>\n"
        "  ] .",
        "  ] .",
    )
    restate_digest(package, MANIFEST)


def undeclared_context_key(package):
    package.edit(CRATE, '      "bridge:cascadeVocabularyPin": "bridge:cascadeVocabularyPin",\n', "")


def term_the_vocabulary_does_not_declare(package):
    package.edit(
        CRATE,
        '      "bridge:cascadeVocabularyPin": "bridge:cascadeVocabularyPin",\n',
        '      "bridge:mappings": "bridge:mappings",\n'
        '      "bridge:cascadeVocabularyPin": "bridge:cascadeVocabularyPin",\n',
    )
    package.edit(
        CRATE,
        '      "bridge:cascadeVocabularyPin": {\n',
        '      "bridge:mappings": {\n'
        '        "@id": "https://example.org/synthetic-adapter/queries/a-typo.rq"\n'
        "      },\n"
        '      "bridge:cascadeVocabularyPin": {\n',
    )


def an_accounting_entry_with_no_verdict(package):
    package.edit(
        ACCOUNTING,
        '  bridge:sourcePath "/ExampleRecord/@Version" ;\n  bridge:verdict bridge:carried .',
        '  bridge:sourcePath "/ExampleRecord/@Version" .',
    )
    restate_digest(package, ACCOUNTING)


def an_accounting_entry_carrying_a_position(package):
    package.edit(ACCOUNTING, '"/ExampleRecord/Note"', '"/ExampleRecord/Note[1]"')
    restate_digest(package, ACCOUNTING)


def an_accounting_entry_padded_with_whitespace(package):
    package.edit(ACCOUNTING, '"/ExampleRecord/Note"', '"/ExampleRecord/ Note "')
    restate_digest(package, ACCOUNTING)


def an_accounting_entry_carrying_no_type(package):
    package.edit(
        ACCOUNTING,
        '[] a bridge:PathEntry ;\n  bridge:sourcePath "/ExampleRecord/Status" ;',
        '[] bridge:sourcePath "/ExampleRecord/Status" ;',
    )
    restate_digest(package, ACCOUNTING)


def an_accounting_entry_for_a_node_in_a_namespace(package):
    package.edit(
        ACCOUNTING,
        '[] a bridge:PathEntry ;\n  bridge:sourcePath "/ExampleRecord/Note" ;',
        "[] a bridge:PathEntry ;\n  bridge:sourcePath \"/ExampleRecord/*[local-name()='Note' and "
        "namespace-uri()='https://example.org/synthetic-adapter/ext/v1']\" ;",
    )
    restate_digest(package, ACCOUNTING)


A_NAMESPACED_SOURCE_PATH = (
    "/ExampleRecord/*[local-name()='Provenance' and namespace-uri()='https://example.org/synthetic-adapter/ext/v1']"
)
THE_NAMESPACED_ENTRY_NAMING_ITS_GAP = (
    f'  bridge:sourcePath "{A_NAMESPACED_SOURCE_PATH}" ;\n'
    "  bridge:verdict bridge:noHome ;\n"
    "  bridge:namesGap ex:no-term-for-provenance-in-an-extension-namespace ."
)


def a_namespaced_entry_whose_verdict_is_no_home_naming_no_gap(package):
    package.edit(
        ACCOUNTING,
        THE_NAMESPACED_ENTRY_NAMING_ITS_GAP,
        f'  bridge:sourcePath "{A_NAMESPACED_SOURCE_PATH}" ;\n  bridge:verdict bridge:noHome .',
    )
    restate_digest(package, ACCOUNTING)


def no_accounting_named_and_no_census_expected(package):
    package.edit(
        MANIFEST,
        "<#example-0004> a bridge:IsomorphicConversionTest ;",
        "<#example-0004> a bridge:InputOnlyTest ;",
    )
    package.edit(
        MANIFEST,
        "  ] ;\n  mf:result [\n"
        "    bridge:expectedGraph <expected/example-0004.ttl> ;\n"
        "    bridge:expectedFindings <findings/example-0004.ttl>\n"
        "  ] .",
        "  ] .",
    )
    package.edit(
        MANIFEST,
        "<#example-0005> a bridge:IsomorphicConversionTest ;",
        "<#example-0005> a bridge:InputOnlyTest ;",
    )
    package.edit(
        MANIFEST,
        "  ] ;\n  mf:result [\n"
        "    bridge:expectedGraph <expected/example-0005.ttl> ;\n"
        "    bridge:expectedFindings <findings/example-0005.ttl>\n"
        "  ] .",
        "  ] .",
    )
    restate_digest(package, MANIFEST)
    crate = package.path / CRATE
    document = json.loads(crate.read_text(encoding="utf-8"))
    root = next(entity for entity in document["@graph"] if entity["@id"] == "./")
    assert "bridge:sourceAccounting" in root
    del root["bridge:sourceAccounting"]
    crate.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="")


A_FINDING_COUNTING_THE_ONE_NODE_IT_STANDS_FOR = """
[] a oa:Annotation ;
  oa:hasTarget [
    oa:hasSource <../in/example-0001.xml> ;
    oa:hasSelector [
      a oa:XPathSelector ;
      rdf:value "/ExampleRecordSet/ExampleRecord[1]" ;
      oa:refinedBy [ a oa:XPathSelector ; rdf:value "Note[1]" ]
    ]
  ] ;
  oa:hasBody ex:no-term-for-a-free-text-note ;
  oa:motivatedBy oa:classifying ;
  sh:value "/ExampleRecord/Note" ;
  <https://ns.cascadeprotocol.org/bridge/v1-draft#occurrences> 1 ;
  sh:resultSeverity sh:Info .
"""


def a_finding_counting_the_one_node_it_stands_for(package):
    written = (package.path / FINDINGS).read_text(encoding="utf-8")
    package.write(FINDINGS, written + A_FINDING_COUNTING_THE_ONE_NODE_IT_STANDS_FOR)
    restate_digest(package, FINDINGS)


STATUSES = "vocab/example-statuses.ttl"

A_LOOKUP_IN_THE_STATUSES = (
    "bridge:lookupIn <example-statuses.ttl> ;\n  bridge:lookupNamesGap ex:a-status-outside-the-set-the-vocabulary-fixes"
)

A_CONCEPT_MAP_OF_THE_THREE_STATUSES = """@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix ex:   <https://example.org/synthetic-adapter/v1#> .

ex:statuses a skos:ConceptScheme .

ex:status-current a skos:Concept ;
  skos:inScheme ex:statuses ;
  skos:notation "current" ;
  skos:exactMatch ex:Current .

ex:status-superseded a skos:Concept ;
  skos:inScheme ex:statuses ;
  skos:notation "superseded" ;
  skos:exactMatch ex:Superseded .

ex:status-withdrawn a skos:Concept ;
  skos:inScheme ex:statuses ;
  skos:notation "withdrawn" ;
  skos:closeMatch ex:Withdrawn .
"""


def describe_turtle(package, relative, name, as_table):
    crate = package.path / CRATE
    document = json.loads(crate.read_text(encoding="utf-8"))
    root = next(entity for entity in document["@graph"] if entity["@id"] == "./")
    if {"@id": relative} not in root["hasPart"]:
        root["hasPart"].append({"@id": relative})
    if as_table:
        document["@context"][1]["bridge:table"] = "bridge:table"
        root["bridge:table"] = {"@id": relative}
    else:
        root.pop("bridge:table", None)
    document["@graph"] = [entity for entity in document["@graph"] if entity["@id"] != relative]
    document["@graph"].append(
        {
            "@id": relative,
            "@type": "File",
            "name": name,
            "encodingFormat": "text/turtle",
            "isBasedOn": {"@id": "https://example.org/synthetic-adapter/vocabulary/statuses"},
            "license": {"@id": "https://spdx.org/licenses/Apache-2.0"},
        }
    )
    crate.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="")


def looking_its_status_up(
    package,
    concept_map=A_CONCEPT_MAP_OF_THE_THREE_STATUSES,
    lookup=A_LOOKUP_IN_THE_STATUSES,
    as_table=True,
):
    package.write(STATUSES, concept_map)
    describe_turtle(package, STATUSES, "Statuses", as_table)
    package.edit(ACCOUNTING, A_LOOKUP_IN_THE_STATUSES, lookup)
    restate_digest(package, ACCOUNTING)


def a_lookup_in_a_concept_map_no_bridge_table_names(package):
    looking_its_status_up(package, as_table=False)


def a_lookup_naming_no_gap(package):
    looking_its_status_up(package, lookup="bridge:lookupIn <example-statuses.ttl>")


def a_gap_for_a_value_outside_a_concept_map_the_entry_names_nowhere(package):
    looking_its_status_up(package, lookup="bridge:lookupNamesGap ex:a-status-outside-the-set-the-vocabulary-fixes")


def a_lookup_naming_a_gap_of_a_kind_other_than_a_value_not_mapped(package):
    looking_its_status_up(
        package,
        lookup="bridge:lookupIn <example-statuses.ttl> ;\n  bridge:lookupNamesGap ex:no-term-for-a-free-text-note",
    )


def a_lookup_naming_a_gap_the_gap_scheme_does_not_declare(package):
    looking_its_status_up(
        package,
        lookup="bridge:lookupIn <example-statuses.ttl> ;\n  bridge:lookupNamesGap ex:a-gap-the-scheme-does-not-hold",
    )


def a_concept_map_carrying_two_concept_schemes(package):
    looking_its_status_up(
        package,
        concept_map=A_CONCEPT_MAP_OF_THE_THREE_STATUSES + "\nex:statuses-of-our-own a skos:ConceptScheme .\n",
    )


def a_concept_map_carrying_no_concept_scheme(package):
    looking_its_status_up(
        package,
        concept_map=A_CONCEPT_MAP_OF_THE_THREE_STATUSES.replace("ex:statuses a skos:ConceptScheme .\n\n", ""),
    )


def a_concept_carrying_two_notations(package):
    looking_its_status_up(
        package,
        concept_map=A_CONCEPT_MAP_OF_THE_THREE_STATUSES.replace(
            'skos:notation "current"', 'skos:notation "current", "Current"'
        ),
    )


def a_concept_matching_no_cascade_term(package):
    looking_its_status_up(
        package,
        concept_map=A_CONCEPT_MAP_OF_THE_THREE_STATUSES.replace(" ;\n  skos:exactMatch ex:Current .", " ."),
    )


def a_concept_whose_notation_is_not_the_key_a_value_is_looked_up_by(package):
    looking_its_status_up(
        package,
        concept_map=A_CONCEPT_MAP_OF_THE_THREE_STATUSES.replace('skos:notation "current"', 'skos:notation " Current"'),
    )


def a_concept_in_a_scheme_other_than_the_one_its_file_carries(package):
    looking_its_status_up(
        package,
        concept_map=A_CONCEPT_MAP_OF_THE_THREE_STATUSES.replace(
            'skos:inScheme ex:statuses ;\n  skos:notation "superseded"',
            'skos:inScheme ex:status ;\n  skos:notation "superseded"',
        ),
    )


def two_concepts_of_one_scheme_carrying_one_notation(package):
    looking_its_status_up(
        package,
        concept_map=A_CONCEPT_MAP_OF_THE_THREE_STATUSES.replace(
            'skos:notation "superseded"', 'skos:notation "current"'
        ),
    )


def a_concept_map_that_is_not_turtle(package):
    looking_its_status_up(package, concept_map="ex:statuses a skos:ConceptScheme .\n")


def profile_not_an_entity(package):
    package.edit(CRATE, '      "@type": ["CreativeWork", "Profile"],', '      "@type": "CreativeWork",')


def pin_not_a_data_entity(package):
    package.edit(
        CRATE,
        '      "@type": ["SoftwareSourceCode", "File"],\n      "name": "synthetic vocabulary at the null commit",',
        '      "@type": "SoftwareSourceCode",\n      "name": "synthetic vocabulary at the null commit",',
    )


@pytest.mark.parametrize(
    "mutate, passes, says, never_says",
    [
        pytest.param(None, True, [], [], id="the fixture package as committed passes"),
        pytest.param(
            identifier_not_a_format_id,
            False,
            ["The adapter carries exactly one identifier, the format id"],
            [],
            id="a shape unmet fails: an identifier that is not a format id",
        ),
        pytest.param(
            adapter_profile_not_named,
            False,
            ["names the Cascade Bridge Adapter profile"],
            [],
            id="a crate that does not name the adapter profile fails",
        ),
        pytest.param(
            expected_graph_not_turtle,
            False,
            ["example-0001: example-0001.ttl does not parse as Turtle"],
            ["sha256 is not this file's"],
            id="a requirement unmet fails: an expected graph that is not Turtle",
        ),
        pytest.param(
            a_finding_selecting_no_node,
            False,
            ["selects no node of example-0001.xml"],
            [],
            id="a requirement unmet fails: a finding selecting no node of its input",
        ),
        pytest.param(
            manifest_not_turtle,
            False,
            ["could not be checked", "manifest.ttl"],
            [],
            id="a requirement that could not run fails: a manifest that is not Turtle",
        ),
        pytest.param(
            no_expected_graphs,
            True,
            [],
            [],
            id="nothing of its kind passes: no expected graphs",
        ),
        pytest.param(
            no_accounting_named_and_no_census_expected,
            True,
            [],
            [],
            id="a crate naming no accounting passes, as every adapter that exists today does",
        ),
        pytest.param(
            an_accounting_entry_with_no_verdict,
            False,
            [
                "An entry carries exactly one bridge:verdict, one of bridge:carried, bridge:carriedInPart, "
                "bridge:redundantWith, bridge:consumed, bridge:noHome, bridge:ignored."
            ],
            [],
            id="a shape the accounting does not meet fails the profile, not only a test running the shapes by hand",
        ),
        pytest.param(
            an_accounting_entry_carrying_a_position,
            False,
            ["/ExampleRecord/Note[1] is written in steps this lint cannot read"],
            [],
            id="a source path carrying a position fails the profile",
        ),
        pytest.param(
            an_accounting_entry_padded_with_whitespace,
            False,
            ["/ExampleRecord/ Note  is written in steps this lint cannot read"],
            [],
            id="a source path padded with whitespace fails the profile",
        ),
        pytest.param(
            an_accounting_entry_carrying_no_type,
            False,
            ["A subject of a bridge:sourcePath is a bridge:PathEntry."],
            [],
            id="an entry carrying no bridge:PathEntry type fails the profile, where it silenced a path before",
        ),
        pytest.param(
            an_accounting_entry_for_a_node_in_a_namespace,
            True,
            [],
            [],
            id="a source path naming a node in a namespace passes the profile",
        ),
        pytest.param(
            a_namespaced_entry_whose_verdict_is_no_home_naming_no_gap,
            False,
            ["An entry whose verdict is bridge:noHome names exactly one bridge:namesGap"],
            [],
            id="a shape's fault over a namespaced entry reaches the report",
        ),
        pytest.param(
            a_finding_counting_the_one_node_it_stands_for,
            False,
            ["bridge:occurrences"],
            [],
            id="a count of one fails the profile, where a count of one is written by omitting it",
        ),
        pytest.param(
            looking_its_status_up,
            True,
            [],
            [],
            id="an entry looking its path's values up in a concept map the crate declares a table passes the profile",
        ),
        pytest.param(
            a_lookup_in_a_concept_map_no_bridge_table_names,
            False,
            ["bridge:table", "example-statuses.ttl"],
            [],
            id="a bridge:lookupIn naming a file no bridge:table names fails the profile",
        ),
        pytest.param(
            a_lookup_naming_no_gap,
            False,
            ["bridge:lookupNamesGap"],
            [],
            id="a bridge:lookupIn with no bridge:lookupNamesGap fails the profile",
        ),
        pytest.param(
            a_gap_for_a_value_outside_a_concept_map_the_entry_names_nowhere,
            False,
            ["bridge:lookupIn"],
            [],
            id="a bridge:lookupNamesGap with no bridge:lookupIn fails the profile",
        ),
        pytest.param(
            a_lookup_naming_a_gap_of_a_kind_other_than_a_value_not_mapped,
            False,
            ["bridge:valueNotMapped", "no-term-for-a-free-text-note"],
            [],
            id="a bridge:lookupNamesGap naming a gap of another kind fails the profile",
        ),
        pytest.param(
            a_lookup_naming_a_gap_the_gap_scheme_does_not_declare,
            False,
            ["bridge:lookupNamesGap", "a-gap-the-scheme-does-not-hold"],
            [],
            id="a bridge:lookupNamesGap naming a gap of no scheme of the adapter fails the profile",
        ),
        pytest.param(
            a_concept_map_carrying_two_concept_schemes,
            False,
            ["example-statuses.ttl", "skos:ConceptScheme"],
            [],
            id="a concept map carrying two skos:ConceptSchemes fails the profile",
        ),
        pytest.param(
            a_concept_map_carrying_no_concept_scheme,
            False,
            ["example-statuses.ttl", "skos:ConceptScheme"],
            [],
            id="a concept map carrying no skos:ConceptScheme fails the profile",
        ),
        pytest.param(
            a_concept_carrying_two_notations,
            False,
            ["skos:notation"],
            [],
            id="a concept carrying two skos:notation fails the profile",
        ),
        pytest.param(
            a_concept_matching_no_cascade_term,
            False,
            ["skos:exactMatch", "skos:closeMatch"],
            [],
            id="a concept matching no Cascade term fails the profile",
        ),
        pytest.param(
            two_concepts_of_one_scheme_carrying_one_notation,
            False,
            ["skos:notation"],
            [],
            id="two concepts of one scheme carrying one skos:notation fail the profile",
        ),
        pytest.param(
            a_concept_whose_notation_is_not_the_key_a_value_is_looked_up_by,
            False,
            ["skos:notation", "under SPARQL's LCASE"],
            [],
            id="a concept whose skos:notation is not already a key fails the profile",
        ),
        pytest.param(
            a_concept_in_a_scheme_other_than_the_one_its_file_carries,
            False,
            ["skos:inScheme", "example-statuses.ttl"],
            [],
            id="a concept skos:inScheme a scheme other than the one its concept map carries fails the profile",
        ),
        pytest.param(
            a_concept_map_that_is_not_turtle,
            False,
            ["example-statuses.ttl", "does not parse as Turtle"],
            [],
            id="a concept map that is not Turtle fails the profile",
        ),
        pytest.param(
            undeclared_context_key,
            False,
            ["is not allowed in the compacted format because it is not present in the @context"],
            [],
            id="RO-Crate 1.2 is inherited: a key the @context does not declare",
        ),
        pytest.param(
            term_the_vocabulary_does_not_declare,
            False,
            ["bridge:mappings is not a term the Cascade Bridge vocabulary declares"],
            [],
            id="a crate carrying a bridge: term the vocabulary does not declare fails",
        ),
        pytest.param(
            profile_not_an_entity,
            False,
            ["MUST reference Profile entities"],
            [],
            id="RO-Crate 1.2 is inherited: what conformsTo names is not typed Profile",
        ),
        pytest.param(
            pin_not_a_data_entity,
            False,
            ["MUST include `File` in its `@type`"],
            [],
            id="RO-Crate 1.2 is inherited: a pin typed SoftwareSourceCode and not File",
        ),
    ],
)
def test_the_validator_runs_the_profile(tracked_package, tmp_path, mutate, passes, says, never_says):
    if mutate:
        mutate(tracked_package)
    report = tmp_path / "report.json"
    run = subprocess.run(
        [
            *ROCRATE_VALIDATOR_IN_THIS_PYTHON,
            "validate",
            str(tracked_package.path),
            "--extra-profiles-path",
            str(ROOT / "adapter"),
            "--profile-identifier",
            "cascade-bridge-adapter",
            "--no-paging",
            "--output-format",
            "json",
            "--output-file",
            str(report),
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=UTF8_OUTPUT_ENV,
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
