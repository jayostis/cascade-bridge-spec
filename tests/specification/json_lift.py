"""A reference JSON lift, written from engine/sparql.md alone, that every JSON lift vector must agree with."""

import base64
import binascii
import json
import re

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import RDF

ROOT_TYPE = URIRef("http://sparql.xyz/facade-x/ns/root")
DATA = "http://sparql.xyz/facade-x/data/"
DECODED = URIRef("https://ns.cascadeprotocol.org/bridge/v1-draft#textDecodedFromBase64")

UCSCHAR = (
    (0xA0, 0xD7FF),
    (0xF900, 0xFDCF),
    (0xFDF0, 0xFFEF),
    *((plane << 16, (plane << 16) | 0xFFFD) for plane in range(1, 14)),
    (0xE1000, 0xEFFFD),
)

A_SEGMENT = re.compile(r"\.([A-Za-z_\u0080-\U0010ffff][A-Za-z0-9_\u0080-\U0010ffff]*)|\['((?:[^'\\]|\\.)*)'\]|\[\*\]")


class NotLifted(ValueError):
    pass


def no_constant(name):
    raise ValueError(f"{name} is not JSON")


class Members(list):
    """An object's members, in order, a repeated name repeated."""


def iunreserved(character):
    if character.isascii():
        return character.isalnum() or character in "-._~"
    return any(low <= ord(character) <= high for low, high in UCSCHAR)


def named(name):
    return URIRef(
        DATA
        + "".join(
            character if iunreserved(character) else "".join(f"%{octet:02X}" for octet in character.encode("utf-8"))
            for character in name
        )
    )


def lone_surrogate_in(text):
    return any(0xD800 <= ord(character) <= 0xDFFF for character in text)


def parsed(data):
    if data.startswith(b"\xef\xbb\xbf"):
        raise NotLifted("a byte order mark")
    try:
        value = json.loads(
            data.decode("utf-8"), object_pairs_hook=Members, parse_float=str, parse_int=str, parse_constant=no_constant
        )
    except (UnicodeDecodeError, ValueError, TypeError) as error:
        raise NotLifted(str(error)) from error
    if not isinstance(value, list):
        raise NotLifted("a value that is neither an object nor an array")

    def check(node):
        if isinstance(node, Members):
            for name, member in node:
                if lone_surrogate_in(name):
                    raise NotLifted("a lone surrogate")
                check(member)
        elif isinstance(node, list):
            for item in node:
                check(item)
        elif isinstance(node, str) and lone_surrogate_in(node):
            raise NotLifted("a lone surrogate")

    check(value)
    return value


def scalar(value):
    if isinstance(value, bool):
        return Literal("true" if value else "false")
    return Literal(value)


def is_container(value):
    return isinstance(value, list)


def segments_of(path):
    if not path.startswith("$"):
        raise ValueError(f"{path} does not start at $")
    segments, rest = [], path[1:]
    while rest:
        found = A_SEGMENT.match(rest)
        if found is None:
            raise ValueError(f"{path} is outside the subset of RFC 9535 a record path is written in")
        if found.group(1) is not None:
            segments.append(found.group(1))
        elif found.group(2) is not None:
            segments.append(json.loads('"' + found.group(2).replace('"', '\\"').replace("\\'", "'") + '"'))
        else:
            segments.append(None)
        rest = rest[found.end() :]
    return segments


def selected(value, path):
    nodes = [value]
    for segment in segments_of(path):
        reached = []
        for node in nodes:
            if isinstance(node, Members):
                reached += [member for name, member in node if segment is None or name == segment]
            elif isinstance(node, list) and segment is None:
                reached += list(node)
        nodes = reached
    return nodes


def records_of(value, path):
    return [node for node in selected(value, path) if isinstance(node, Members)]


def names_text(content_type):
    main, *parameters = content_type.split(";")
    kind, slash, _ = main.strip().partition("/")
    if not slash or kind.lower() != "text":
        return False
    for parameter in parameters:
        name, _, value = parameter.partition("=")
        if name.strip().lower() == "charset" and value.strip().strip('"').lower() != "utf-8":
            return False
    return True


def decoded(container):
    members = dict(reversed(container))
    content_type, data = members.get("contentType"), members.get("data")
    if not (isinstance(content_type, str) and isinstance(data, str) and names_text(content_type)):
        return None
    written = re.sub(r"[ \t\r\n]", "", data)
    try:
        octets = base64.b64decode(written, validate=True)
        if base64.b64encode(octets).decode("ascii") != written:
            return None
        return octets.decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return None


def lift(value, records=()):
    """The lift of a document's value, each node of `records` lifted as the envelope skeleton lifts a record."""
    graph = Graph()
    emptied = {id(record) for record in records}

    def node_for(container):
        subject = BNode()
        emptying = id(container) in emptied
        if isinstance(container, Members):
            pairs = [(named(name), member) for name, member in container]
        else:
            pairs = [(RDF[f"_{number}"], item) for number, item in enumerate(container, start=1)]
        for predicate, member in pairs:
            if member is None or (emptying and is_container(member)):
                continue
            graph.add((subject, predicate, node_for(member) if is_container(member) else scalar(member)))
        text = decoded(container) if isinstance(container, Members) and not records else None
        if text is not None:
            graph.add((subject, DECODED, Literal(text)))
        return subject

    graph.add((node_for(value), RDF.type, ROOT_TYPE))
    return graph


def lifted(data):
    return lift(parsed(data))


def skeleton(data, path):
    value = parsed(data)
    return lift(value, records_of(value, path))


def applies_to(media_type):
    return media_type in ("application/json",) or media_type.endswith("+json")
