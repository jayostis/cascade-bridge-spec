"""Check 2: the crate and the test manifest conform to this repository's shapes."""

from __future__ import annotations

from pyshacl import validate as shacl_validate
from rdflib import Graph
from rdflib.namespace import RDF, SH

from ..result import failed, passed
from ..terms import BRIDGE, SHAPES, SPEC_PIN_ONLY

HEADING = "2. SHACL, crate and test manifest as one graph"
TITLE = "the crate and the test manifest conform to the shapes"


def run(crate):
    conforms, report, _ = shacl_validate(
        crate.graph,
        shacl_graph=Graph().parse(SHAPES, format="turtle"),
        advanced=True,          # the shapes use sh:sparql constraints
        allow_warnings=True,    # warnings are reported below, not failed on
        inplace=False,
    )

    violations, warnings = [], []
    for found in report.subjects(RDF.type, SH.ValidationResult):
        severity = report.value(found, SH.resultSeverity)
        path = report.value(found, SH.resultPath)
        message = str(report.value(found, SH.resultMessage) or "").strip()
        (violations if severity == SH.Violation else warnings).append((path, message))

    missing_spec_pin = (crate.root, BRIDGE.specPin, None) not in crate.graph
    only_spec_pin = bool(violations) and all(
        path == BRIDGE.specPin for path, _ in violations
    )

    if conforms and not violations:
        result = passed("the crate and the test manifest conform").verdict(
            True,
            f"{SHAPES.name} against the crate and {crate.manifest_file.name}",
        )
    elif only_spec_pin and missing_spec_pin:
        result = failed(SPEC_PIN_ONLY).verdict(
            False,
            SPEC_PIN_ONLY,
            "The adapter's root entity carries no bridge:specPin: the",
            "commit of this specification it is written against, a",
            "SoftwareSourceCode entity in the crate with codeRepository",
            "and version (the full SHA), the same shape as",
            "bridge:vocabularyPin. Nothing else about the crate or the",
            "test manifest is wrong. adapter/ro-crate-metadata.md.",
        )
    else:
        detail = ["including a missing bridge:specPin"] if missing_spec_pin else []
        detail += [f"{path or '-'}: {message}" for path, message in violations]
        result = failed(f"{len(violations)} shape violation(s)").verdict(
            False, f"{len(violations)} violation(s)", *detail
        )

    for path, message in warnings:
        result.says("warn", f"{path or '-'}: {message}")
    return result
