"""The repository an adapter reads its ontologies and shapes from: which version a run picks, and what it reads there."""

from dataclasses import dataclass

from compatibility_tool import git, packages, picking, placing
from compatibility_tool.console import Status, Stop, detail, first_line, note, report
from compatibility_tool.document import CRATE, crate_root, is_adapter, referenced_id
from compatibility_tool.github import repository_name, repository_path, url_on_this_server
from compatibility_tool.record import Role, Row

PIN = "bridge:cascadeVocabularyPin"
NAMED_FILE = "bridge:vocabularyFile"
VOCABULARY = "bridge:vocabulary"

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
OWL_ONTOLOGY = "http://www.w3.org/2002/07/owl#Ontology"


@dataclass(frozen=True)
class Reading:
    """Where an adapter's vocabularies are read from, at which commit, and which files of it."""

    url: str
    commit: str
    files: tuple[str, ...]


def strings(root, key):
    value = root.get(key)
    listed = value if isinstance(value, list) else [value]
    return [entry for entry in listed if isinstance(entry, str)]


def named_iris(root, key):
    value = root.get(key)
    listed = value if isinstance(value, list) else [value]
    return [entry["@id"] for entry in listed if isinstance(entry, dict) and isinstance(entry.get("@id"), str)]


def pinned(adapter):
    nodes, root = crate_root(adapter)
    named = referenced_id(root, PIN)
    entity = nodes.get(named) or {}
    url, commit = referenced_id(entity, "codeRepository"), entity.get("version")
    if not isinstance(url, str) or not isinstance(commit, str):
        raise Stop(
            f"{adapter / CRATE} names {PIN} {named}, which carries no codeRepository and version: "
            "the repository the vocabularies are read from, and the commit they are read at"
        )
    return Reading(url_on_this_server(repository_path(url)), commit, tuple(strings(root, NAMED_FILE)))


def read_from(directory, counterparts):
    """The one vocabulary every adapter of this run reads; none where the run pairs nothing, and runs nothing."""
    if not counterparts:
        return None
    adapters = [directory] if is_adapter(directory) else [entry.path for entry in counterparts]
    pins, files = [], []
    for adapter in adapters:
        if adapter is None or not is_adapter(adapter):
            continue
        reading = pinned(adapter)
        if (reading.url, reading.commit) not in pins:
            pins.append((reading.url, reading.commit))
        files += [name for name in reading.files if name not in files]
    if not pins:
        return None
    if len(pins) > 1:
        raise Stop(
            f"the adapters of this run name one {PIN} or the run cannot check one version out for them: "
            + ", ".join(f"{url} at {commit}" for url, commit in pins)
        )
    return Reading(*pins[0], tuple(files))


def place(directory, reading, options, event, reached):
    name = repository_name(reading.url)
    if options.mode == "local":
        return placing.on_disk(name, reading.url, placing.sibling(directory, reading.url), Role.VOCABULARY)
    into = directory.parent / name
    if picking.merging(reached, repository_path(reading.url)):
        return placing.in_ci(reading.url, reached, event, into, Role.VOCABULARY)
    picking.remove(into)
    if not git.clone_at(reading.url, into, reading.commit):
        raise Stop(f"{reading.url} holds no commit {reading.commit}, which is what the adapter's {PIN} names")
    return Row(
        name=name,
        repository=reading.url,
        commit=reading.commit,
        how=f"the adapter's {PIN}",
        role=Role.VOCABULARY,
        path=into,
    )


def compared(row, reading):
    """What the sibling holds on disk, against the bytes the pinned commit holds."""
    if git.local_commit(row.path, reading.commit) is None:
        note(f"{row.name} on disk holds no commit {reading.commit}, so the comparison was not made")
        return
    for name in reading.files:
        on_disk = row.path / name
        if on_disk.is_file() and git.blob(row.path, reading.commit, name) == on_disk.read_bytes():
            continue
        note(f"{name} on disk is not what {reading.commit} holds")


def faulty(adapter, path, files):
    rdflib = packages.installed("rdflib")
    _, root = crate_root(adapter)
    declared = set()
    for name in files:
        named = path / name
        if not named.is_file():
            yield f"{name} is no file of {path}, where this run reads the adapter's vocabularies"
            continue
        graph = rdflib.Graph()
        try:
            graph.parse(named, format="turtle")
        except Exception as error:
            yield f"{name} does not parse as Turtle: {first_line(str(error))}"
            continue
        declared.update(str(found) for found in graph.subjects(rdflib.URIRef(RDF_TYPE), rdflib.URIRef(OWL_ONTOLOGY)))
    for namespace in named_iris(root, VOCABULARY):
        if namespace not in declared:
            yield f"{namespace} is a {VOCABULARY} no {NAMED_FILE} declares an owl:Ontology"


def check(directory, row, reading):
    """The crate's paths, against the vocabularies the run checked out; a counterpart's are never checked."""
    if not is_adapter(directory):
        return Status.OK
    print(f"Each {NAMED_FILE}, in {row.path}")
    faults = list(faulty(directory, row.path, reading.files))
    for fault in faults:
        detail(fault)
    if faults:
        report(False, f"{directory} does not read the vocabularies it names")
        return Status.FAIL
    report(True, f"every {NAMED_FILE} is a file there, declaring every {VOCABULARY} the adapter writes")
    return Status.OK


def behind(directory, named, api, into):
    """Each merged pull request of the vocabulary whose commit the adapter's pin does not contain."""
    if not is_adapter(directory):
        return
    reading = pinned(directory)
    path = repository_path(reading.url)
    for entry in named:
        if entry.path != path:
            continue
        pull = api.pull_request(entry)
        head = pull.get("head", {}).get("sha")
        if not pull.get("merged") or not head or contains(reading, head, into):
            continue
        yield f"{entry.label} merged at {head}, and the adapter's {PIN}, {reading.commit}, does not contain it"


def contains(reading, commit, into):
    picking.remove(into)
    git.init(into)
    if not all(git.fetched(reading.url, wanted, into) for wanted in (reading.commit, commit)):
        return False
    return git.holds(into, reading.commit, commit)
