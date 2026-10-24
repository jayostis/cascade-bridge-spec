"""A second implementation of how a Bridge versions a mapped graph, sharing no code with any Bridge.

python tests/specification/versioning.py MAPPED.nt
"""

import base64
import hashlib
import re
import sys

PLACEHOLDER = "urn:cascade:this-version"
SPECIALIZATION_OF = "http://www.w3.org/ns/prov#specializationOf"
ARRIVED_AS = "https://ns.cascadeprotocol.org/bridge/v1-draft#arrivedAs"
XSD_STRING = "http://www.w3.org/2001/XMLSchema#string"


def ni_name(octets):
    digest = hashlib.sha256(octets).digest()
    return "ni:///sha-256;" + base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


# An IRI is ("iri", text), a blank node ("blank", label), a literal ("literal", lexical form, datatype IRI).

_ESCAPES = {"t": "\t", "b": "\b", "n": "\n", "r": "\r", "f": "\f", '"': '"', "'": "'", "\\": "\\"}
_IRI = r"<([^<>\"{}|^`\\\x00-\x20]*)>"
_BLANK = r"_:([A-Za-z0-9_]+)"
_LITERAL = r"\"((?:[^\"\\\n\r]|\\.)*)\"(?:\^\^" + _IRI + r"|(@[A-Za-z0-9-]+))?"
_TRIPLE = re.compile(rf"^\s*(?:{_IRI}|{_BLANK})\s*{_IRI}\s*(?:{_IRI}|{_BLANK}|{_LITERAL})\s*\.\s*$")


def _unescaped(text):
    def one(match):
        escape = match.group(0)
        if escape[1] in "uU":
            return chr(int(escape[2:], 16))
        return _ESCAPES[escape[1]]

    return re.sub(r"\\(?:u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8}|[tbnrf\"'\\])", one, text)


def parsed_ntriples(text):
    triples = set()
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _TRIPLE.match(line)
        if not match:
            raise ValueError(f"line {number} is not an N-Triples triple: {line!r}")
        subject, blank_subject, predicate, iri, blank, lexical, datatype, language = match.groups()
        if language:
            raise ValueError(f"line {number}: a language-tagged literal is beyond this implementation")
        if iri is not None:
            obj = ("iri", _unescaped(iri))
        elif blank is not None:
            obj = ("blank", blank)
        else:
            obj = ("literal", _unescaped(lexical), _unescaped(datatype) if datatype else XSD_STRING)
        head = ("iri", _unescaped(subject)) if subject is not None else ("blank", blank_subject)
        triples.add((head, ("iri", _unescaped(predicate)), obj))
    return triples


def _canonical_term(term):
    if term[0] == "blank":
        raise ValueError(f"a version holding a blank node is beyond the rule: _:{term[1]}")
    if term[0] == "iri":
        if re.search(r"[\x00-\x20<>\"{}|^`\\]", term[1]):
            raise ValueError(f"an IRI this implementation cannot write canonically: {term[1]!r}")
        return f"<{term[1]}>"
    lexical, datatype = term[1], term[2]
    if re.search(r"[\x00-\x09\x0b\x0c\x0e-\x1f\x7f]", lexical):
        raise ValueError(f"a control character whose canonical escape this implementation leaves open: {lexical!r}")
    text = lexical.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
    return f'"{text}"' if datatype == XSD_STRING else f'"{text}"^^<{datatype}>'


def canonical_nquads(triples):
    return "".join(sorted({" ".join(map(_canonical_term, triple)) + " .\n" for triple in triples}))


def _in_version(term, version):
    return term[0] == "iri" and (term[1] == version or term[1].startswith(version + "#"))


def _renamed(term, version, name):
    if _in_version(term, version):
        return ("iri", name + term[1][len(version) :])
    return term


def _dropped(triples, drafts):
    """The graph without the drafted versions, their content, what arrived as them, and every blank node only what
    it drops reaches."""
    arrivals = {subject for subject, predicate, obj in triples if predicate[1] == ARRIVED_AS and obj[1] in drafts}
    kept = {
        triple
        for triple in triples
        if triple[0] not in arrivals and not any(_in_version(triple[0], draft) for draft in drafts)
    }
    while True:
        reached = {obj for _, _, obj in kept if obj[0] == "blank"}
        orphaned = {triple for triple in kept if triple[0][0] == "blank" and triple[0] not in reached}
        orphaned = {triple for triple in orphaned if any(o == triple[0] for _, _, o in triples)}
        if not orphaned:
            return kept
        kept -= orphaned


def versions(triples):
    """Each version's name, its canonical content, and the graph with every version named, one kept of each record."""
    records = {subject[1]: obj for subject, predicate, obj in triples if predicate[1] == SPECIALIZATION_OF}
    drafts = sorted(records)
    if len(drafts) != sum(1 for _, predicate, _ in triples if predicate[1] == SPECIALIZATION_OF):
        raise ValueError("a version with more than one prov:specializationOf")
    contents = {}
    for version in drafts:
        if "#" in version:
            raise ValueError(f"a version's IRI carries a fragment: {version}")
        content = {
            tuple(_renamed(term, version, PLACEHOLDER) for term in triple)
            for triple in triples
            if _in_version(triple[0], version)
        }
        nquads = canonical_nquads(content)
        contents[version] = (ni_name(nquads.encode("utf-8")), nquads)
    kept = {}
    for version in drafts:
        record = records[version]
        if record not in kept or (contents[version][0], version) < (contents[kept[record]][0], kept[record]):
            kept[record] = version
    graph = _dropped(set(triples), set(drafts) - set(kept.values()))
    named = {}
    for version in kept.values():
        name, nquads = contents[version]
        named[name] = nquads
        graph = {tuple(_renamed(term, version, name) for term in triple) for triple in graph}
    return named, graph


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as mapped:
        named, graph = versions(parsed_ntriples(mapped.read()))
    for name, nquads in named.items():
        print(name)
        print(nquads)
