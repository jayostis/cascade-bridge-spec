import json
from pathlib import Path

from compatibility_tool.console import Stop
from compatibility_tool.github import repository_name

SPEC_ROOT = Path(__file__).resolve().parents[2]

FILE = "compatibility.json"
CRATE = "ro-crate-metadata.json"
CONTEXT_IRI = "https://ns.cascadeprotocol.org/bridge/v1-draft/compatibility.jsonld"

ENGINE_KEYS = ("setup", "command")
TOP_KEYS = {"@context", "mustPassWith", *ENGINE_KEYS}
PICKED_WHEN_THE_CHECK_RUNS = "which version of it is picked when the check runs"


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


def referenced_id(node, key):
    value = node.get(key)
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    return value.get("@id") if isinstance(value, dict) else None


def counterparts(document):
    listed = (document or {}).get("mustPassWith")
    return [entry for entry in listed if isinstance(entry, str)] if isinstance(listed, list) else []


def problems_json_ld_hides_from_shacl(document):
    problems = [f"{key} is not a key the context defines" for key in document if key not in TOP_KEYS]
    if "specPin" in document:
        problems.append(
            f"specPin was removed: nothing names a version of cascade-bridge-spec, {PICKED_WHEN_THE_CHECK_RUNS}"
        )
    for key in ENGINE_KEYS:
        if key in document and not isinstance(document[key], list):
            problems.append(f"{key} is an argument vector, written as a JSON array of strings")
    listed = document.get("mustPassWith")
    if "mustPassWith" in document and not isinstance(listed, list):
        problems.append("mustPassWith is a list of repositories, written as a JSON array, even of one")
    for entry in listed if isinstance(listed, list) else []:
        if not isinstance(entry, str):
            problems.append(f"a mustPassWith entry is a repository URL, {PICKED_WHEN_THE_CHECK_RUNS}: {entry!r}")
    return problems


def name_clashes(directory, urls):
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
        "cascade-bridge-spec": "that is where the check checks the specification out beside this repository",
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
            f"{FILE} carries no {', '.join(carried)}: it is run rather than running anything"
        )
    if not is_adapter(directory) and len(carried) != len(ENGINE_KEYS):
        return f"{directory} holds no {CRATE}, so it is an engine, and an engine's {FILE} carries setup and command"
    return None
