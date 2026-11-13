"""forms = path_forms.read(graph, adapter)         # the crate's graph and its bridge:Adapter node
form, place = path_forms.place_of(forms, path)  # a bridge:sourcePath
"""

from dataclasses import dataclass

from rdflib import URIRef

BRIDGE = "https://ns.cascadeprotocol.org/bridge/v1-draft#"


@dataclass(frozen=True)
class Form:
    envelope: URIRef
    prefix: str
    contained: bool
    kind: str | None


def read(graph, adapter):
    """The forms the adapter's envelopes declare, the longest prefix first."""
    forms = []
    for envelope in graph.objects(adapter, URIRef(BRIDGE + "envelope")):
        content, contained, kind = (
            graph.value(envelope, URIRef(BRIDGE + term))
            for term in ("pathOfContentInRecord", "pathOfContainedContentBelowContent", "pathOfRecordKindBelowContent")
        )
        if content is contained is kind is None:
            continue
        content = "" if content is None else str(content)
        for prefix, is_contained in ((content, False), (None if contained is None else content + str(contained), True)):
            if prefix is not None:
                forms.append(Form(envelope, prefix, is_contained, None if kind is None else prefix + str(kind)))
    return sorted(forms, key=lambda form: (-len(form.prefix), form.prefix, str(form.envelope)))


def place_of(forms, path):
    """The form a path was written in, the longest prefix a / follows, and the path after it; else no form and the path."""
    for form in forms:
        if path.startswith(form.prefix + "/"):
            return form, path[len(form.prefix) :]
    return None, path
