import json
import os
import subprocess
import sys

from compatibility_tool.console import Status, Stop, detail, report
from compatibility_tool.document import (
    CONTEXT_IRI,
    CRATE,
    FILE,
    SPEC_ROOT,
    counterparts,
    form_problem,
    is_adapter,
    name_clashes,
    problems_json_ld_hides_from_shacl,
)


def installed(name):
    try:
        return __import__(name)
    except ImportError:
        pass
    if os.environ.get("CI") == "true":
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--quiet",
                "--group",
                f"{SPEC_ROOT / 'pyproject.toml'}:validators",
            ],
            check=False,
        )
    try:
        return __import__(name)
    except ImportError as error:
        raise Stop(
            f"{name} is not installed, and the checks read the shapes with it: "
            "python3 -m pip install --group <cascade-bridge-spec>/pyproject.toml:validators"
        ) from error


def form_problems(directory, document):
    """What the context hides from SHACL, read with the standard library alone."""
    if document is None:
        return []
    if not isinstance(document, dict) or document.get("@context") != CONTEXT_IRI:
        found = document.get("@context") if isinstance(document, dict) else document
        return [f"its @context is {found!r}, where a {FILE} names {CONTEXT_IRI}"]
    problems = problems_json_ld_hides_from_shacl(document) + name_clashes(directory, counterparts(document))
    form = form_problem(directory, document)
    return [*problems, form] if form else problems


def shape_violations(directory, document, spec):
    rdflib = installed("rdflib")
    pyshacl = installed("pyshacl")
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
        "rocrate-validator",
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
