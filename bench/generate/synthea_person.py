"""python3 bench/generate/synthea_person.py <synthea output folder> <synthea person id> <out.json.gz | out.xml.gz>"""

import argparse
import gzip
import json
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from repeat_entries import ENTRY, digest_line

NAME = "Bench Hospital"
ADDRESS = "1 Bench Street"
TELECOM = "555-0100"
CITY = "Bench City"
ZIP = "000000000"

KINDS = {".json.gz": ("fhir", ".json"), ".xml.gz": ("ccda", ".xml")}
PROVIDER_TYPES = ("Organization", "Location")

NINE_DIGITS = re.compile(r"\d{9}")
ALNUM_RUN = re.compile(r"[^\W_]+")
BOUNDED = r"(?<![^\W_]){}(?![^\W_])"
JSON_STRING = re.compile(r'("(?:[^"\\]|\\.)*")(\s*:)?')
XML_PART = re.compile(r"(<!--[\s\S]*?-->|<!\[CDATA\[[\s\S]*?\]\]>)|(<[^>]*>)|([^<]+)")
XML_ATTRIBUTE = re.compile(r"""(=\s*)("[^"]*"|'[^']*')""")
XML_ENTITY = re.compile(r"&(#x[0-9a-fA-F]+|#[0-9]+|amp|lt|gt|quot|apos);")
XML_NAMED = {"amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'"}


class Matcher:
    def __init__(self, replacements):
        self.indexed = {}
        self.unindexed = []
        for text, placeholder in replacements.items():
            pattern = re.compile(BOUNDED.format(re.escape(text)), re.IGNORECASE)
            first = ALNUM_RUN.search(text.lower())
            if first:
                self.indexed.setdefault(first.group(), []).append((pattern, placeholder))
            else:
                self.unindexed.append((pattern, placeholder))

    def hits(self, text):
        words = set(ALNUM_RUN.findall(text.lower()))
        candidates = [candidate for word in words for candidate in self.indexed.get(word, ())] + self.unindexed
        found = [
            (match.start(), match.end(), placeholder)
            for pattern, placeholder in candidates
            for match in pattern.finditer(text)
        ]
        found.sort(key=lambda hit: (hit[0], hit[0] - hit[1]))
        chosen, end = [], 0
        for hit in found:
            if hit[0] >= end:
                chosen.append(hit)
                end = hit[1]
        return chosen


def removed_values(hospital_documents):
    names, addresses, cities, zips, telecoms = [], [], [], [], []
    for document in hospital_documents:
        for entry in document.get("entry", []):
            resource = entry["resource"]
            if resource["resourceType"] in PROVIDER_TYPES and isinstance(resource.get("name"), str):
                names.append(resource["name"])
            address = resource.get("address") or []
            for part in address if isinstance(address, list) else [address]:
                addresses.extend(part.get("line", []))
                cities.append(part.get("city"))
                code = part.get("postalCode")
                if isinstance(code, str) and NINE_DIGITS.fullmatch(code):
                    zips.append(code)
            for telecom in resource.get("telecom", []):
                if telecom.get("system") == "phone" and isinstance(telecom.get("value"), str):
                    telecoms.append(telecom["value"])
    replacements = {}
    for values, placeholder in ((names, NAME), (addresses, ADDRESS), (cities, CITY), (zips, ZIP), (telecoms, TELECOM)):
        for value in values:
            if value:
                replacements.setdefault(value, placeholder)
    return replacements


def json_forms(value):
    return {value, json.dumps(value, ensure_ascii=False)[1:-1], json.dumps(value)[1:-1]}


def xml_forms(value):
    return {
        value,
        escape(value),
        escape(value, {'"': "&quot;", "'": "&apos;"}),
        escape(value, {'"': "&quot;", "'": "&#39;"}),
    }


def written_as(replacements, forms):
    return {form: placeholder for value, placeholder in replacements.items() for form in forms(value)}


def unescape_xml(text):
    def character(match):
        name = match.group(1)
        if name in XML_NAMED:
            return XML_NAMED[name]
        return chr(int(name[2:], 16) if name[1] == "x" else int(name[1:]))

    return XML_ENTITY.sub(character, text)


def json_units(text):
    for match in JSON_STRING.finditer(text):
        if not match.group(2):
            written = match.group(1)[1:-1]
            yield written, json.loads(match.group(1)) if "\\" in written else written


def xml_units(text):
    for match in XML_PART.finditer(text):
        raw, tag, content = match.groups()
        if raw:
            yield raw, raw
        elif tag:
            for attribute in XML_ATTRIBUTE.finditer(tag):
                written = attribute.group(2)[1:-1]
                yield written, unescape_xml(written)
        else:
            yield content, unescape_xml(content)


def substitute(text, hits):
    pieces, position = [], 0
    for start, end, placeholder in hits:
        pieces.append(text[position:start])
        pieces.append(placeholder)
        position = end
    pieces.append(text[position:])
    return "".join(pieces)


class Replaced:
    def __init__(self):
        self.whole = 0
        self.inside = 0

    def count(self, written, hits):
        if len(hits) == 1 and hits[0][0] == 0 and hits[0][1] == len(written):
            self.whole += 1
        else:
            self.inside += 1


def scrub_json(text, matcher, replaced):
    def string(match):
        if match.group(2):
            return match.group(0)
        written = match.group(1)[1:-1]
        hits = matcher.hits(written)
        if not hits:
            return match.group(0)
        replaced.count(written, hits)
        return '"' + substitute(written, hits) + '"'

    return JSON_STRING.sub(string, text)


def scrub_xml(text, matcher, replaced):
    def unit(written):
        hits = matcher.hits(written)
        if not hits:
            return written
        replaced.count(written, hits)
        return substitute(written, hits)

    def attribute(match):
        quote = match.group(2)[0]
        return match.group(1) + quote + unit(match.group(2)[1:-1]) + quote

    def part(match):
        raw, tag, content = match.groups()
        if raw:
            return unit(raw)
        if tag:
            return XML_ATTRIBUTE.sub(attribute, tag)
        return unit(content)

    return XML_PART.sub(part, text)


def leftovers(units, plain):
    return sum(len(plain.hits(read)) for _, read in units)


def find_person(folder, person_id, kind):
    subfolder, suffix = kind
    found = sorted((folder / subfolder).glob(f"*_{person_id}{suffix}"))
    if len(found) != 1:
        raise SystemExit(f"{len(found)} {suffix} files for {person_id} in {folder / subfolder}")
    return found[0]


def read_hospital_documents(folder):
    paths = sorted((folder / "fhir").glob("hospitalInformation*.json")) + sorted(
        (folder / "fhir").glob("practitionerInformation*.json")
    )
    if not paths:
        raise SystemExit(f"no hospitalInformation or practitionerInformation file in {folder / 'fhir'}")
    return [json.loads(path.read_text(encoding="utf-8")) for path in paths]


def scrubbed_record(folder, person_id, kind):
    replacements = removed_values(read_hospital_documents(folder))
    with open(find_person(folder, person_id, kind), encoding="utf-8", newline="") as handle:
        text = handle.read()
    replaced = Replaced()
    if kind[1] == ".json":
        forms, scrub, units = json_forms, scrub_json, json_units
    else:
        forms, scrub, units = xml_forms, scrub_xml, xml_units
    text = scrub(text, Matcher(written_as(replacements, forms)), replaced)
    left = leftovers(units(text), Matcher({value: "" for value in replacements}))
    if left:
        raise SystemExit(f"{left} removed values are left in the record of {person_id}; nothing is written")
    return text, replaced


def entry_count(text, kind):
    return len(json.loads(text)["entry"]) if kind[1] == ".json" else len(ENTRY.findall(text))


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("person")
    parser.add_argument("out", type=Path)
    arguments = parser.parse_args(argv)
    kind = next((kind for suffix, kind in KINDS.items() if arguments.out.name.endswith(suffix)), None)
    if kind is None:
        parser.error(f"out ends in one of {', '.join(KINDS)}")

    text, replaced = scrubbed_record(arguments.folder, arguments.person, kind)
    document = text.encode("utf-8")
    written = gzip.compress(document, compresslevel=9, mtime=0)
    arguments.out.write_bytes(written)
    print(digest_line("document", document), "entries", entry_count(text, kind))
    print(digest_line("file", written))
    print("replaced whole", replaced.whole, "inside", replaced.inside)


if __name__ == "__main__":
    main(sys.argv[1:])
