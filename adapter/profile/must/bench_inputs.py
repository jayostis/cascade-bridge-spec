import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gzip
import hashlib
import json
import zlib
from collections import Counter
from urllib.parse import urljoin

from jsonschema import Draft202012Validator
from rdflib import URIRef
from rdflib.namespace import RDF
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement

from _findings import report_findings
from _terms import BRIDGE, SCHEMA

SCHEMA_FILE = Path(__file__).resolve().parents[3] / "bench" / "manifest.schema.json"
MANIFEST = "bench/manifest.json"
CRATE = "ro-crate-metadata.json"

WANTED = {
    "inputs": "at least one input",
    "id": "a lower-case segment, [a-z0-9][a-z0-9._-]*",
    "path": "a POSIX path from the adapter's root, with no empty, . or .. segment and no leading /",
    "sha256": "64 lower-case hexadecimal digits",
    "bytes": "a whole number of bytes, 0 or more",
    "envelope": "a non-empty reference resolved against ro-crate-metadata.json, as ro-crate-metadata.json#envelope-name",
    "measures": "at least one distinct lower-case segment, none of them timeout or refused",
    "onPullRequests": "true or false",
    "timeoutSeconds": "a whole number of seconds, 1 or more",
}


def where(path):
    return "".join(f"[{step}]" if isinstance(step, int) else f".{step}" for step in path).lstrip(".")


def nonconforming(manifest):
    for error in sorted(
        Draft202012Validator(json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))).iter_errors(manifest),
        key=lambda e: list(map(str, e.absolute_path)),
    ):
        path = list(error.absolute_path)
        if error.validator == "required":
            for member in error.validator_value:
                if member not in error.instance:
                    yield f"{where(path + [member])}: is missing; wanted {WANTED[member]}"
        elif error.validator == "additionalProperties":
            allowed = ", ".join(error.schema["properties"])
            yield f"{where(path)}: {error.message}; the members are {allowed}"
        else:
            member = next((step for step in reversed(path) if step in WANTED), "inputs")
            yield f"{where(path)}: {error.message}; wanted {WANTED[member]}"


def content_of(file):
    data = file.read_bytes()
    return gzip.decompress(data) if file.suffix == ".gz" else data


def faulty_input(crate, index, entry):
    name = f"inputs[{index}] ({entry['id']})"
    prefix = f"{crate.graph.value(crate.root, SCHEMA.identifier)}-"
    if not entry["id"].startswith(prefix):
        yield f"{name}: id does not start with {prefix}, the crate's identifier and a hyphen, which keeps ids unique across adapters"

    envelope = entry.get("envelope")
    if envelope is not None:
        resolved = URIRef(urljoin((crate.adapter / CRATE).resolve().as_uri(), envelope))
        if (resolved, RDF.type, BRIDGE.Envelope) not in crate.graph:
            known = ", ".join(
                sorted(f"{CRATE}#{str(e).partition('#')[2]}" for e in crate.graph.subjects(RDF.type, BRIDGE.Envelope))
            )
            yield f"{name}: envelope {envelope} names no bridge:Envelope of the crate; wanted one of {known}"

    file = crate.adapter / entry["path"]
    if not file.is_file():
        yield f"{name}: path {entry['path']} is not a file in this package"
        return
    try:
        data = content_of(file)
    except (OSError, EOFError, zlib.error) as error:
        yield f"{name}: {entry['path']} is not a gzip file: {error}"
        return
    if hashlib.sha256(data).hexdigest() != entry["sha256"]:
        yield (
            f"{name}: sha256 is not that of the bytes the measured thing is given, {entry['path']} gunzipped where it ends in .gz\n"
            f"manifest   {entry['sha256']}\n"
            f"recomputed {hashlib.sha256(data).hexdigest()}"
        )
    if len(data) != entry["bytes"]:
        yield f"{name}: bytes is not the size of {entry['path']} gunzipped where it ends in .gz\nmanifest   {entry['bytes']}\nrecomputed {len(data)}"


def faulty(crate):
    file = crate.adapter / MANIFEST
    if not file.is_file():
        return
    manifest = json.loads(file.read_text(encoding="utf-8"))
    unconforming = list(nonconforming(manifest))
    for message in unconforming:
        yield f"{MANIFEST}: {message}"
    if unconforming:
        return
    for id, count in Counter(entry["id"] for entry in manifest["inputs"]).items():
        if count > 1:
            yield f"{MANIFEST}: id {id} appears {count} times; wanted each id once"
    for index, entry in enumerate(manifest["inputs"]):
        for message in faulty_input(crate, index, entry):
            yield f"{MANIFEST}: {message}"


@requirement(name="Benchmark inputs")
class BenchInputs(PyFunctionCheck):
    """An adapter's bench/manifest.json, where it has one, names inputs that are there and are what it says."""

    @check(name="every benchmark input is the file and the digest the manifest says")
    def run_check(self, context: ValidationContext) -> bool:
        return report_findings(self, context, faulty)
