"""A second implementation of record names and version names, sharing no code with any Bridge.

python tests/specification/recomputed.py name INPUT...
python tests/specification/recomputed.py base-url URL
python tests/specification/recomputed.py versions MAPPED.nt
"""

import base64
import hashlib
import re
import sys
from urllib.parse import urlsplit, urlunsplit

NAMESPACE = "90c60849-c5ef-4ca6-bfb8-8662bd07d2b5"
PLACEHOLDER = "urn:cascade:this-version"
SPECIALIZATION_OF = "http://www.w3.org/ns/prov#specializationOf"
XSD_STRING = "http://www.w3.org/2001/XMLSchema#string"


def record_name(inputs):
    digest = bytearray(hashlib.sha256("|".join([NAMESPACE, *inputs]).encode("utf-8")).digest()[:16])
    digest[6] = (digest[6] & 0x0F) | 0x80
    digest[8] = (digest[8] & 0x3F) | 0x80
    text = digest.hex()
    return f"urn:uuid:{text[:8]}-{text[8:12]}-{text[12:16]}-{text[16:20]}-{text[20:]}"


def normalised_base_url(url):
    parts = urlsplit(url)
    userinfo, at, hostport = parts.netloc.rpartition("@")
    host, colon, port = hostport.rpartition(":") if not hostport.endswith("]") else (hostport, "", "")
    if not colon or not port.isdigit():
        host, colon, port = hostport, "", ""
    netloc = f"{userinfo}{at}{host.lower()}{colon}{port}"
    return urlunsplit((parts.scheme.lower(), netloc, parts.path, parts.query, parts.fragment)).rstrip("/")


def ni_name(octets):
    digest = hashlib.sha256(octets).digest()
    return "ni:///sha-256;" + base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


# N-Triples without blank nodes: an IRI is ("iri", text), a literal ("literal", lexical form, datatype IRI).

_ESCAPES = {"t": "\t", "b": "\b", "n": "\n", "r": "\r", "f": "\f", '"': '"', "'": "'", "\\": "\\"}
_IRI = r"<([^<>\"{}|^`\\\x00-\x20]*)>"
_LITERAL = r"\"((?:[^\"\\\n\r]|\\.)*)\"(?:\^\^" + _IRI + r"|(@[A-Za-z0-9-]+))?"
_TRIPLE = re.compile(rf"^\s*{_IRI}\s*{_IRI}\s*(?:{_IRI}|{_LITERAL})\s*\.\s*$")


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
            raise ValueError(f"line {number} is not an N-Triples triple of IRIs and literals: {line!r}")
        subject, predicate, iri, lexical, datatype, language = match.groups()
        if language:
            raise ValueError(f"line {number}: a language-tagged literal is beyond this implementation")
        if iri is not None:
            obj = ("iri", _unescaped(iri))
        else:
            obj = ("literal", _unescaped(lexical), _unescaped(datatype) if datatype else XSD_STRING)
        triples.add((("iri", _unescaped(subject)), ("iri", _unescaped(predicate)), obj))
    return triples


def _canonical_term(term):
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


def _renamed(term, version, name):
    if term[0] == "iri" and (term[1] == version or term[1].startswith(version + "#")):
        return ("iri", name + term[1][len(version) :])
    return term


def _in_version(term, version):
    return term[0] == "iri" and (term[1] == version or term[1].startswith(version + "#"))


def versions(triples):
    """Each version's name, its canonical content, and the graph with every version named."""
    drafts = sorted(subject[1] for subject, predicate, _ in triples if predicate[1] == SPECIALIZATION_OF)
    if len(drafts) != len(set(drafts)):
        raise ValueError("a version with more than one prov:specializationOf")
    named, graph = {}, set(triples)
    for version in drafts:
        if "#" in version:
            raise ValueError(f"a version's IRI carries a fragment: {version}")
        content = {
            tuple(_renamed(term, version, PLACEHOLDER) for term in triple)
            for triple in triples
            if _in_version(triple[0], version)
        }
        nquads = canonical_nquads(content)
        name = ni_name(nquads.encode("utf-8"))
        named[name] = nquads
        graph = {tuple(_renamed(term, version, name) for term in triple) for triple in graph}
    return named, graph


if __name__ == "__main__":
    command, *arguments = sys.argv[1:]
    if command == "name":
        print(record_name(arguments))
    elif command == "base-url":
        print(normalised_base_url(arguments[0]))
    elif command == "versions":
        with open(arguments[0], encoding="utf-8") as mapped:
            named, graph = versions(parsed_ntriples(mapped.read()))
        for name, nquads in named.items():
            print(name)
            print(nquads)
        print(canonical_nquads(graph), end="")
    else:
        sys.exit(__doc__)
