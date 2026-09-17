from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from _terms import BRIDGE, MF


def path_of(iri):
    return Path(url2pathname(urlparse(str(iri)).path))


def file_name_of(iri):
    return path_of(iri).name or str(iri)


@dataclass(frozen=True)
class Crate:
    adapter: Path
    graph: Graph
    root: URIRef
    manifest_iri: URIRef
    manifest_file: Path

    def path_in_package(self, iri):
        prefix = self.adapter.resolve().as_uri().rstrip("/") + "/"
        return path_of(iri) if str(iri).startswith(prefix) else None

    def file_at(self, iri):
        path = self.path_in_package(iri)
        return path if path is not None and path.is_file() else None

    @property
    def entries(self):
        head = self.graph.value(self.manifest_iri, MF.entries)
        return [] if head is None else list(self.graph.items(head))

    def name_of(self, test):
        return str(self.graph.value(test, MF.name) or test)


def load(adapter):
    crate_file = adapter / "ro-crate-metadata.json"
    graph = Graph()
    graph.parse(crate_file, format="json-ld", base=crate_file.resolve().as_uri())

    roots = list(graph.subjects(RDF.type, BRIDGE.Adapter))
    if len(roots) != 1:
        raise ValueError(
            f"the crate declares {len(roots)} bridge:Adapter entities; exactly one, the root entity, is expected"
        )
    root = roots[0]

    manifests = list(graph.objects(root, BRIDGE.testManifest))
    if len(manifests) != 1:
        raise ValueError(f"the adapter names {len(manifests)} bridge:testManifest values; exactly one is expected")
    manifest_iri = manifests[0]
    manifest_file = path_of(manifest_iri)
    if not manifest_file.is_file():
        raise ValueError(f"the adapter's bridge:testManifest names {manifest_file}, which does not exist")
    try:
        graph.parse(manifest_file, format="turtle", publicID=str(manifest_iri))
    except Exception as error:
        raise ValueError(f"{manifest_file.name} does not parse as Turtle: {error}") from error

    return Crate(adapter, graph, root, manifest_iri, manifest_file)


_parsed_crates: dict[Path, Crate] = {}


def from_context(context):
    uri = context.settings.rocrate_uri
    for candidate in (getattr(uri, "path", None), str(uri)):
        if not candidate:
            continue
        text = str(candidate)
        path = path_of(text) if text.startswith("file://") else Path(text)
        if path.is_dir():
            path = path.resolve()
            if path not in _parsed_crates:
                _parsed_crates[path] = load(path)
            return _parsed_crates[path]
    raise FileNotFoundError(f"cannot read {uri} as a directory")
