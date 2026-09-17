import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from compatibility_tool.console import Status, Stop, report

SPEC_ROOT = Path(__file__).resolve().parents[2]

FILE = "compatibility.json"
CRATE = "ro-crate-metadata.json"
CONTEXT_IRI = "https://ns.cascadeprotocol.org/bridge/v1-draft/compatibility.jsonld"

ENGINE_KEYS = ("specPin", "setup", "command")
TOP_KEYS = {"@context", "mustPassWith", *ENGINE_KEYS}
PIN_KINDS = ("commit", "tag", "branch")
PIN_KEYS = {"codeRepository", *PIN_KINDS}


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as error:
        raise Stop(f"{path} is not JSON: {error}") from error


def read_file(directory):
    path = directory / FILE
    return read_json(path) if path.is_file() else None


def is_adapter(directory):
    return (directory / CRATE).is_file()


def crate_root(directory):
    crate = read_json(directory / CRATE)
    nodes = {node.get("@id"): node for node in crate.get("@graph", [])}
    return nodes, nodes.get("./") or {}


def repository_name(url):
    name = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
    return name.removesuffix(".git")


@dataclass(frozen=True)
class Pin:
    label: str
    repository: str
    kind: str
    value: str

    @property
    def name(self):
        return repository_name(self.repository)

    def __str__(self):
        return f"{self.label}: {self.repository} {self.kind} {self.value}"


def pin_from(label, entry):
    kinds = [kind for kind in PIN_KINDS if kind in entry] if isinstance(entry, dict) else []
    if len(kinds) != 1 or not isinstance(entry.get("codeRepository"), str):
        raise Stop(f"{label} is not a pin; run validate first")
    return Pin(label, entry["codeRepository"], kinds[0], entry[kinds[0]])


def entries(document):
    return [pin_from("mustPassWith", entry) for entry in (document or {}).get("mustPassWith", [])]


def spec_pin(directory, document):
    if not is_adapter(directory):
        if not document or "specPin" not in document:
            raise Stop(
                f"{directory} holds no {CRATE}, so it is an engine, and an "
                f"engine states its spec pin as specPin in {FILE}"
            )
        return pin_from("specPin", document["specPin"])
    nodes, root = crate_root(directory)
    pin = root.get("bridge:specPin")
    entity = nodes.get(pin.get("@id")) if isinstance(pin, dict) else None
    if not entity:
        raise Stop(f"{directory / CRATE} names no bridge:specPin entity")
    repository = entity.get("codeRepository")
    if isinstance(repository, dict):
        repository = repository.get("@id")
    if not repository or not entity.get("version"):
        raise Stop(f"the crate's bridge:specPin, {pin['@id']}, carries no codeRepository and version to pin")
    return Pin("bridge:specPin", repository, "commit", entity["version"])


def problems_json_ld_hides_from_shacl(document):
    problems = [f"{key} is not a key the context defines" for key in document if key not in TOP_KEYS]
    for key in ("setup", "command"):
        if key in document and not isinstance(document[key], list):
            problems.append(f"{key} is an argument vector, written as a JSON array of strings")
    if "mustPassWith" in document and not isinstance(document["mustPassWith"], list):
        problems.append("mustPassWith is a list of pins, written as a JSON array, even of one")
    if "specPin" in document and not isinstance(document["specPin"], dict):
        problems.append("specPin is one pin, written as a JSON object")
    for label in ("specPin", "mustPassWith"):
        value = document.get(label)
        for pin in value if isinstance(value, list) else [value]:
            if isinstance(pin, dict):
                problems += [
                    f"{key}, in {label}, is not a key the context defines" for key in pin if key not in PIN_KEYS
                ]
    return problems


def name_clashes(directory, document):
    listed = document.get("mustPassWith")
    urls = [
        pin["codeRepository"]
        for pin in (listed if isinstance(listed, list) else [])
        if isinstance(pin, dict) and isinstance(pin.get("codeRepository"), str)
    ]
    problems = []
    seen = {}
    for url in urls:
        name = repository_name(url)
        if name.casefold() in seen:
            problems.append(
                "Each repository name appears in mustPassWith at most once, "
                f"compared without case: {seen[name.casefold()]} and {url} "
                f"would both be checked out at ../{name}"
            )
        seen[name.casefold()] = url
    reserved = {
        "cascade-bridge-spec": "that is where the starter checks the specification out beside this repository",
        directory.resolve().name.casefold(): "that is this repository's own directory",
    }
    for url in urls:
        name = repository_name(url)
        if name.casefold() in reserved:
            problems.append(
                f"No repository in mustPassWith is named {name}, compared without case: {reserved[name.casefold()]}"
            )
    return problems


def form_problem(directory, document):
    carried = [key for key in ENGINE_KEYS if key in document]
    if is_adapter(directory) and carried:
        return (
            f"{directory} holds {CRATE}, so it is an adapter, and an adapter's "
            f"{FILE} carries no {', '.join(carried)}: its spec pin is the "
            "crate's bridge:specPin, and it is run rather than running anything"
        )
    if not is_adapter(directory) and not carried:
        return (
            f"{directory} holds no {CRATE}, so it is an engine, and an engine's "
            f"{FILE} carries specPin, setup and command"
        )
    return None


def spec_pin_command(directory, options):
    print("The specification pin")
    pin = spec_pin(directory, read_file(directory))
    report(True, str(pin))
    if options.output:
        with open(options.output, "a", encoding="utf-8") as handle:
            handle.write(f"repository={pin.repository}\nkind={pin.kind}\nref={pin.value}\n")
    return Status.OK
