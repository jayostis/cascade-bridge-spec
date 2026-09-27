import json
import re
from decimal import Decimal
from urllib.parse import quote, unquote

from _terms import BRIDGE

RFC_6901 = "https://www.rfc-editor.org/rfc/rfc6901"
JSON_MEDIA_TYPE = re.compile(r"^(application/json|[a-z]+/[a-z0-9.!#$&^_-]+[+]json)$")
XML_MEDIA_TYPE = re.compile(r"^(application/xml|text/xml|[a-z]+/[a-z0-9.!#$&^_-]+[+]xml)$")
NAME_FIRST = r"A-Za-z_\u0080-퟿-\U0010ffff"
A_SEGMENT = re.compile(rf"\.([{NAME_FIRST}][{NAME_FIRST}0-9]*)|\['((?:[^'\\]|\\.)*)'\]|\[\*\]")
A_PATH = re.compile(r"^(/(?:[^/~]|~[01])+)+$")
FRAGMENT_SAFE = "/?:@!$&'()*+,;=-._~"


class NotJson(ValueError):
    pass


class Members(list):
    """An object's (name, value) pairs in document order, a repeated name repeated."""


def syntax_of(crate):
    declared = str(crate.graph.value(crate.root, BRIDGE.sourceMediaType) or "")
    if JSON_MEDIA_TYPE.match(declared):
        return "json"
    if XML_MEDIA_TYPE.match(declared):
        return "xml"
    return None


def _refuse_constant(name):
    raise ValueError(f"{name} is not JSON")


def parsed(data):
    """The document's value, each object as Members and each number as the text the document writes."""
    if data.startswith(b"\xef\xbb\xbf"):
        raise NotJson("it begins with a byte order mark")
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=Members,
            parse_float=str,
            parse_int=str,
            parse_constant=_refuse_constant,
        )
    except (UnicodeDecodeError, ValueError) as error:
        raise NotJson(str(error)) from error
    if any(lone_surrogate_in(text) for text in texts_of(value)):
        raise NotJson("it escapes a lone surrogate")
    return value


def texts_of(node):
    """Every member name and string a value holds."""
    if isinstance(node, str):
        yield node
    for name, child in children(node):
        if is_object(node):
            yield name
        yield from texts_of(child)


def lone_surrogate_in(text):
    return any(0xD800 <= ord(character) <= 0xDFFF for character in text)


def validated_value(data):
    """The document's value as a JSON Schema validator reads it."""
    return json.loads(data.decode("utf-8-sig"), parse_float=Decimal, parse_constant=_refuse_constant)


def children(node):
    """Each (reference token, value) a node holds, in document order."""
    if isinstance(node, Members):
        return list(node)
    if isinstance(node, dict):
        return list(node.items())
    if isinstance(node, list):
        return [(str(index), item) for index, item in enumerate(node)]
    return []


def is_object(node):
    return isinstance(node, (Members, dict))


def segments_of(path):
    """Each segment of a record path, a name or None for the wildcard; ValueError outside the subset."""
    if not path.startswith("$"):
        raise ValueError(f"{path} does not start at $")
    segments, rest = [], path[1:]
    while rest:
        found = A_SEGMENT.match(rest)
        if found is None:
            raise ValueError(f"{path} is outside the subset of RFC 9535 JSONPath a record path is written in")
        if found.group(1) is not None:
            segments.append(found.group(1))
        elif found.group(2) is not None:
            segments.append(json.loads('"' + found.group(2).replace('"', '\\"').replace("\\'", "'") + '"'))
        else:
            segments.append(None)
        rest = rest[found.end() :]
    return segments


def records_of(value, path):
    """Each (reference tokens, record) the record path selects, in document order."""
    reached = [((), value)]
    for segment in segments_of(path):
        reached = [
            (tokens + (token,), child)
            for tokens, node in reached
            for token, child in children(node)
            if (segment is None and (is_object(node) or isinstance(node, list)))
            or (segment is not None and is_object(node) and token == segment)
        ]
    return [(tokens, node) for tokens, node in reached if is_object(node)]


def pointer_of(tokens):
    """A JSON Pointer in its URI fragment identifier representation, without the #."""
    return "".join("/" + quote(token.replace("~", "~0").replace("/", "~1"), safe=FRAGMENT_SAFE) for token in tokens)


def tokens_of(pointer):
    """The reference tokens of a pointer in its fragment representation, or None where it is not one."""
    if pointer == "":
        return ()
    if not pointer.startswith("/"):
        return None
    tokens = []
    try:
        unescaped = unquote(pointer, errors="strict")
    except UnicodeDecodeError:
        return None
    for escaped in unescaped[1:].split("/"):
        if re.search(r"~(?![01])", escaped):
            return None
        tokens.append(escaped.replace("~1", "/").replace("~0", "~"))
    return tuple(tokens)


def selected_by(value, pointer):
    """Each (reference tokens, node) a pointer selects: none, one, or more through a repeated name."""
    tokens = tokens_of(pointer)
    if tokens is None:
        return []
    reached = [((), value)]
    for token in tokens:
        reached = [
            (walked + (token,), child) for walked, node in reached for name, child in children(node) if name == token
        ]
    return reached


UCSCHAR = (
    (0xA0, 0xD7FF),
    (0xF900, 0xFDCF),
    (0xFDF0, 0xFFEF),
    *((plane << 16, (plane << 16) | 0xFFFD) for plane in range(1, 14)),
    (0xE1000, 0xEFFFD),
)


def iunreserved(character):
    if character.isascii():
        return character.isalnum() or character in "-._~"
    return any(low <= ord(character) <= high for low, high in UCSCHAR)


def named_in_the_lift(name):
    """A member's name as the lift appends it to the data namespace."""
    return "".join(
        character if iunreserved(character) else "".join(f"%{octet:02X}" for octet in character.encode("utf-8"))
        for character in name
    )
