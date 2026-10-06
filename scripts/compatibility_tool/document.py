import json

from compatibility_tool.console import Stop
from compatibility_tool.github import repository_name

FILE = "compatibility.json"
CRATE = "ro-crate-metadata.json"
RUNTIME = "cascade-runtime.json"
CONTEXT_IRI = "https://ns.cascadeprotocol.org/bridge/v1-draft/compatibility.jsonld"
ADAPTER_TYPE = "bridge:Adapter"

VECTORS = ("setup", "command")
HOST_KEYS = {"name", "release", *VECTORS}
RELEASE_KEYS = {"asset", "path", "command"}
TOP_KEYS = {"@context", "host", "mustPassWith", *VECTORS}
PICKED_WHEN_THE_CHECK_RUNS = "which version of it is picked when the check runs"


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as error:
        raise Stop(f"{path} is not JSON: {error}") from error


def read_file(directory):
    path = directory / FILE
    return read_json(path) if path.is_file() else None


def is_vocabulary(directory):
    """A crate whose root is typed, and not bridge:Adapter: the terms and queries adapters and runtimes read."""
    if not (directory / CRATE).is_file():
        return False
    _, root = crate_root(directory)
    types = root.get("@type")
    return bool(types) and ADAPTER_TYPE not in (types if isinstance(types, list) else [types])


def is_adapter(directory):
    return (directory / CRATE).is_file() and not is_vocabulary(directory)


def is_runtime(directory):
    return not (directory / CRATE).is_file() and (directory / RUNTIME).is_file()


def kind(directory):
    return "an adapter" if is_adapter(directory) else "a runtime" if is_runtime(directory) else "an engine"


def named_repositories(directory):
    """Each repository cascade-runtime.json names, as it writes it."""
    document = read_json(directory / RUNTIME)
    if not isinstance(document, dict):
        raise Stop(f"{directory / RUNTIME} is not a JSON object")
    adapters = document.get("adapters", [])
    if not isinstance(adapters, list):
        raise Stop(f"{directory / RUNTIME} names adapters by no JSON array")
    entries = [("vocabulary", document.get("vocabulary"))]
    entries += [(f"adapters[{index}]", entry) for index, entry in enumerate(adapters)]
    named = []
    for where, entry in entries:
        repository = entry.get("repository") if isinstance(entry, dict) else None
        if not isinstance(repository, str):
            raise Stop(f"{directory / RUNTIME} names {where} by no repository")
        named.append((where, repository))
    return named


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


def hosts(document):
    listed = (document or {}).get("host")
    return listed if isinstance(listed, list) else []


def vector_problems(node):
    return [
        f"{key} is an argument vector, written as a JSON array of strings"
        for key in VECTORS
        if key in node and not isinstance(node[key], list)
    ]


def problems_json_ld_hides_from_shacl(document):
    problems = [f"{key} is not a key the context defines" for key in document if key not in TOP_KEYS]
    problems += vector_problems(document)
    listed = document.get("host", [])
    if not isinstance(listed, list) or not all(isinstance(host, dict) for host in listed):
        problems.append("host is a list of hosts, written as a JSON array of objects, even of one")
    for host in hosts(document):
        if isinstance(host, dict):
            problems += [f"{key} is not a key a host carries" for key in host if key not in HOST_KEYS]
            problems += vector_problems(host)
            release = host.get("release", {})
            if not isinstance(release, dict):
                problems.append("a host's release is a JSON object")
                continue
            problems += [f"{key} is not a key a host's release carries" for key in release if key not in RELEASE_KEYS]
            problems += vector_problems(release)
    listed = document.get("mustPassWith")
    if "mustPassWith" in document and not isinstance(listed, list):
        problems.append("mustPassWith is a list of repositories, written as a JSON array, even of one")
    for entry in listed if isinstance(listed, list) else []:
        if not isinstance(entry, str):
            problems.append(f"a mustPassWith entry is a repository URL, {PICKED_WHEN_THE_CHECK_RUNS}: {entry!r}")
    return problems


def name_clashes(directory, urls, listing="mustPassWith"):
    reserved = {
        "cascade-bridge-spec": "that is where the check checks the specification out beside this repository",
        directory.resolve().name.casefold(): "that is this repository's own directory",
    }
    clashes = []
    seen = {}
    for url in urls:
        name = repository_name(url)
        folded = name.casefold()
        if folded in seen:
            clashes.append(
                f"Each repository name appears in {listing} at most once, "
                f"compared without case: {seen[folded]} and {url} would both be checked out at ../{name}"
            )
        if folded in reserved:
            clashes.append(f"No repository in {listing} is named {name}, compared without case: {reserved[folded]}")
        seen[folded] = url
    return clashes


def form_problem(directory, document):
    carried = [key for key in ("host", *VECTORS) if key in document]
    if is_vocabulary(directory):
        found = f"{directory} holds a {CRATE} whose root is no {ADAPTER_TYPE}, so it is a vocabulary"
        if carried:
            return f"{found}, and a vocabulary's {FILE} carries no {', '.join(carried)}: the runtimes it names are run"
        return None if counterparts(document) else f"{found}, and a vocabulary's {FILE} names a runtime in mustPassWith"
    if is_adapter(directory) and carried:
        return (
            f"{directory} holds {CRATE}, so it is an adapter, and an adapter's "
            f"{FILE} carries no {', '.join(carried)}: it is run rather than running anything"
        )
    if is_adapter(directory):
        return None
    if is_runtime(directory):
        found = f"{directory} holds {RUNTIME}, so it is a runtime"
        if "mustPassWith" in document:
            return f"{found}, and a runtime's {FILE} names no mustPassWith: its counterparts are what {RUNTIME} names"
    else:
        found = f"{directory} holds no {CRATE}, so it is an engine"
    if not hosts(document):
        return f"{found}, and {kind(directory)}'s {FILE} names at least one host"
    if not all(isinstance(host, dict) and all(key in host for key in VECTORS) for host in hosts(document)):
        return f"{found}, and each host of it carries setup and command"
    return None


def problems(directory, document):
    """What the JSON-LD context hides from SHACL, read with the standard library alone."""
    if document is None:
        return []
    if not isinstance(document, dict) or document.get("@context") != CONTEXT_IRI:
        found = document.get("@context") if isinstance(document, dict) else document
        return [f"its @context is {found!r}, where a {FILE} names {CONTEXT_IRI}"]
    found = problems_json_ld_hides_from_shacl(document) + name_clashes(directory, counterparts(document))
    if is_runtime(directory):
        found += name_clashes(directory, [url for _, url in named_repositories(directory)], RUNTIME)
    form = form_problem(directory, document)
    return [*found, form] if form else found
