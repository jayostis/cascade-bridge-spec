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


def shortened(term):
    return str(term).replace(str(BRIDGE), "bridge:")


def last_step_of(path):
    """The element or attribute a path ends at, as a mapping writes it: a facade-X lift erases the leading @."""
    return str(path).rsplit("/", 1)[-1].removeprefix("@")


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

    for entry, source_path, verdict in entries:
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
        if verdict not in VERDICTS_CLAIMING_CARRIAGE or mentioned is None:
            continue
        step = last_step_of(source_path)
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
