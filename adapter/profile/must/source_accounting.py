import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re

from rdflib import Graph
from rdflib.namespace import RDF, SKOS
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement

from _codes import scheme_named_by
from _findings import SHAPES, report_findings, unmet
from _terms import BRIDGE

THE_KIND_A_VERDICT_IMPLIES = {
    BRIDGE.carriedInPart: BRIDGE.carriedWithLoss,
    BRIDGE.noHome: BRIDGE.noPredicate,
}

VERDICTS_CLAIMING_CARRIAGE = (BRIDGE.carried, BRIDGE.carriedInPart)

A_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]*")

IN_NO_NAMESPACE = r"[^\s/\[\]'*@=():]+"

A_STEP = re.compile(
    rf"/(?P<attribute>@?)"
    rf"(?:(?P<name>{IN_NO_NAMESPACE})"
    rf"|\*\[local-name\(\)='(?P<local>{IN_NO_NAMESPACE})' and namespace-uri\(\)='[^']*'\])"
)

A_PATH_IS_STEPS = (
    "where a step of a bridge:sourcePath follows a /, and is an element's name or, for a node in a namespace, "
    "the step an oa:XPathSelector writes for it, an attribute's step that form after an @, "
    "and no step carries a position"
)


def shortened(term):
    return str(term).replace(str(BRIDGE), "bridge:")


def steps_of(source_path):
    """Each step of a path, or None where the path is written as no sequence of steps."""
    steps, rest = [], source_path
    while rest:
        found = A_STEP.match(rest)
        if found is None:
            return None
        steps.append(found)
        rest = rest[found.end() :]
    return steps or None


def name_of(step):
    """The element or attribute a step names, as a mapping writes it: a facade-X lift erases the leading @."""
    return step["local"] or step["name"]


def ill_formed(source_path, steps, record):
    if steps is None:
        yield f"{source_path} is written in steps this lint cannot read, {A_PATH_IS_STEPS}"
        return
    if len(steps) < 2:
        yield f"{source_path} is the record element alone, where a bridge:sourcePath names a node below it"
        return
    if any(step["attribute"] for step in steps[:-1]):
        yield (
            f"{source_path} writes @ before a step that is not its last, where an attribute is the node a path ends at"
        )
        return
    first = name_of(steps[0])
    if record and first != record:
        yield (
            f"{source_path} starts at {first}, where a bridge:sourcePath starts at {record}, "
            "the adapter's bridge:elementNameOfEachRecord"
        )


def mentioned_by_the_mappings(crate):
    """Every name the adapter's mappings write, or None where one of them is not a file this lint can read."""
    mentioned = set()
    for mapping in crate.graph.objects(crate.root, BRIDGE.mapping):
        path = crate.file_at(mapping)
        if path is None:
            return None
        mentioned.update(A_NAME.findall(path.read_text(encoding="utf-8")))
    return mentioned


def entries_of(accounting):
    for entry in accounting.subjects(RDF.type, BRIDGE.PathEntry):
        path = accounting.value(entry, BRIDGE.sourcePath)
        verdict = accounting.value(entry, BRIDGE.verdict)
        if path is not None and verdict is not None:
            yield entry, str(path), verdict


def repeated(accounted):
    seen, twice = set(), set()
    for path in accounted:
        if path in seen:
            twice.add(path)
        seen.add(path)
    return twice


def faulty(crate):
    named = sorted(crate.graph.objects(crate.root, BRIDGE.sourceAccounting))
    if not named:
        return
    if len(named) > 1:
        yield (
            "the adapter names more than one bridge:sourceAccounting, where every path of a source "
            "is accounted for in one file"
        )
        return
    path = crate.file_at(named[0])
    if path is None:
        yield f"bridge:sourceAccounting names {named[0]}, which is not a file in this package"
        return
    accounting = Graph()
    try:
        accounting.parse(path, format="turtle")
    except Exception as error:
        yield f"{path.name} does not parse as Turtle\n{error}"
        return

    shapes = Graph().parse(SHAPES, format="turtle")
    for message in unmet(accounting, shapes):
        yield f"{path.name}: {message}"

    entries = sorted(entries_of(accounting), key=lambda entry: entry[1])
    accounted = [source_path for _, source_path, _ in entries]
    for shared in sorted(repeated(accounted)):
        yield f"{shared} is the bridge:sourcePath of more than one entry, where a path is accounted for once"

    scheme = scheme_named_by(crate)
    gaps = set(scheme.subjects(RDF.type, SKOS.Concept))
    mentioned = mentioned_by_the_mappings(crate)
    record = str(crate.graph.value(crate.root, BRIDGE.elementNameOfEachRecord) or "")

    for entry, source_path, verdict in entries:
        steps = steps_of(source_path)
        yield from ill_formed(source_path, steps, record)
        for instead in sorted(accounting.objects(entry, BRIDGE.sameFactAs)):
            if str(instead) == source_path:
                yield (
                    f"{source_path} names its own bridge:sourcePath as its bridge:sameFactAs, "
                    "where the fact is carried by another path"
                )
            elif str(instead) not in accounted:
                yield (
                    f"{source_path} names {instead} as its bridge:sameFactAs, "
                    f"which is the bridge:sourcePath of no entry of {path.name}"
                )
        for gap in sorted(accounting.objects(entry, BRIDGE.namesGap)):
            if gap not in gaps:
                yield (
                    f"{source_path} names {gap} as its bridge:namesGap, "
                    "which is no gap of the adapter's bridge:gapScheme"
                )
                continue
            wanted = THE_KIND_A_VERDICT_IMPLIES.get(verdict)
            if wanted is None:
                continue
            kinds = set(scheme.objects(gap, SKOS.broader))
            if wanted not in kinds:
                yield (
                    f"{source_path} names {gap}, which is skos:broader "
                    f"{', '.join(sorted(shortened(kind) for kind in kinds)) or 'nothing'}, where an entry whose "
                    f"verdict is {shortened(verdict)} names a gap skos:broader {shortened(wanted)}"
                )
        if verdict not in VERDICTS_CLAIMING_CARRIAGE or mentioned is None or steps is None:
            continue
        step = name_of(steps[-1])
        if step not in mentioned:
            yield (
                f"{source_path} is {shortened(verdict)}, where no bridge:mapping of this adapter mentions {step}: "
                "a path nothing reads reaches no graph"
            )


@requirement(name="Source accounting")
class SourceAccounting(PyFunctionCheck):
    """An adapter naming a source accounting names one, and every entry in it holds against the rest of the crate."""

    @check(name="the adapter names one source accounting and every entry in it holds")
    def run_check(self, context: ValidationContext) -> bool:
        return report_findings(self, context, faulty)
