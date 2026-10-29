"""The text values the XML lift writes on an element, written from engine/sparql.md alone, that every XML lift
vector must agree with."""

import re

from lxml import etree

WHITESPACE = re.compile(r"[ \t\r\n]+")
BREAK = object()


def local_name(element):
    return element.tag.rsplit("}", 1)[-1]


def text_content(element):
    return "".join(element.itertext())


def holds_text(element):
    return WHITESPACE.fullmatch(text_content(element) or " ") is None


def pieces(element, breaking, top=True):
    breaks = not top and local_name(element) in breaking
    if breaks:
        yield BREAK
    if element.text:
        yield element.text
    for child in element:
        yield from pieces(child, breaking, top=False)
        if child.tail:
            yield child.tail
    if breaks:
        yield BREAK


def text_with_element_breaks(element, breaking):
    runs, run = [], []
    for piece in pieces(element, breaking):
        if piece is BREAK:
            runs.append("".join(run))
            run = []
        else:
            run.append(piece)
    runs.append("".join(run))
    lines = (WHITESPACE.sub(" ", run).strip(" ") for run in runs)
    return "\n".join(line for line in lines if line)


def elements(data):
    parser = etree.XMLParser(remove_comments=True, remove_pis=True, resolve_entities=False)
    return etree.fromstring(data, parser).iter()
