import json
import subprocess

from compatibility_tool import packages
from compatibility_tool.console import Status, detail, report
from compatibility_tool.document import CRATE, FILE, is_adapter


def shape_violations(directory, document, spec):
    rdflib = packages.installed("rdflib")
    pyshacl = packages.installed("pyshacl")
    context = json.loads((spec / "vocab" / "compatibility.context.jsonld").read_text(encoding="utf-8"))["@context"]
    data = dict(document, **{"@context": context})
    graph = rdflib.Graph().parse(data=json.dumps(data), format="json-ld", base=(directory / FILE).resolve().as_uri())
    shapes = rdflib.Graph().parse(spec / "shapes" / "bridge.shapes.ttl", format="turtle")
    conforms, results, _ = pyshacl.validate(graph, shacl_graph=shapes, advanced=True, inplace=False)
    if conforms:
        return []
    from rdflib.namespace import RDF, SH

    return sorted(
        {
            str(results.value(result, SH.resultMessage) or "").strip()
            for result in results.subjects(RDF.type, SH.ValidationResult)
        }
    )


def lint_adapter(directory, spec):
    argv = [
        packages.validator(),
        "validate",
        str(directory),
        "--extra-profiles-path",
        str(spec / "adapter"),
        "--profile-identifier",
        "cascade-bridge-adapter",
        "--no-paging",
        "--verbose",
    ]
    print(f"  run   {' '.join(argv)}")
    return subprocess.run(argv).returncode == 0


def validate(directory, document, spec):
    print(f"{FILE} and, in an adapter, the crate")
    if is_adapter(directory) and not lint_adapter(directory, spec.path):
        report(False, f"{directory} does not pass the Cascade Bridge Adapter profile")
        return Status.FAIL
    if document is None:
        if is_adapter(directory):
            return Status.OK
        report(False, f"{directory} holds no {CRATE}, so it is an engine, and an engine states {FILE}")
        return Status.FAIL
    violations = shape_violations(directory, document, spec.path)
    for message in violations:
        detail(message)
    if violations:
        report(False, f"{len(violations)} shape violation(s)")
        return Status.FAIL
    report(True, f"{FILE} against the shapes")
    return Status.OK
