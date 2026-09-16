"""The adapter's crate and test manifest, loaded as one graph.

Base IRIs are the point. The crate is parsed with ro-crate-metadata.json's own
location as base and the manifest with its own, which is what makes the two
files one graph: the crate's "./" and the manifest's <../> become the same IRI,
the adapter; the crate's "fixtures/manifest.ttl" and the manifest's <> become
the same IRI; and the manifest's <../ro-crate-metadata.json#envelope-efetch>
resolves onto the envelope entity the crate declares. Load either file with the
wrong base and every link between them silently becomes two unrelated nodes,
and the shapes report nothing rather than reporting a mistake.

Every check after the first takes one of these, so each walk from a test to its
input, to its envelope's schema and to its expected graph crosses between the
two files without matching on file names.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from .terms import BRIDGE, MF


@dataclass(frozen=True)
class Crate:
    """An adapter package, loaded."""

    adapter: Path
    graph: Graph
    root: URIRef
    manifest_iri: URIRef
    manifest_file: Path

    def path_of(self, iri):
        """The file an entity IRI names, when it is one inside the package.

        None for a remote entity: an https: IRI is a reference, and there are
        no committed bytes here to hold it to.
        """
        prefix = self.adapter.resolve().as_uri().rstrip("/") + "/"
        if not str(iri).startswith(prefix):
            return None
        return Path(url2pathname(urlparse(str(iri)).path))

    def file_at(self, iri):
        """The committed file an IRI names, or None if there is not one."""
        path = self.path_of(iri)
        return path if path is not None and path.is_file() else None

    @property
    def entries(self):
        """The tests in mf:entries, in the order the manifest lists them."""
        head = self.graph.value(self.manifest_iri, MF.entries)
        found = []
        while head is not None and head != RDF.nil:
            member = self.graph.value(head, RDF.first)
            if member is not None:
                found.append(member)
            head = self.graph.value(head, RDF.rest)
        return found

    def name_of(self, test):
        return str(self.graph.value(test, MF.name) or test)


def entity_name(iri):
    """The file name at the end of an entity IRI, for a message."""
    return Path(url2pathname(urlparse(str(iri)).path)).name or str(iri)


def load(adapter):
    """Load the crate and the test manifest it names as one graph."""
    crate_file = adapter / "ro-crate-metadata.json"
    graph = Graph()
    graph.parse(crate_file, format="json-ld", base=crate_file.resolve().as_uri())

    roots = list(graph.subjects(RDF.type, BRIDGE.Adapter))
    if len(roots) != 1:
        raise SystemExit(
            f"  FAIL  the crate declares {len(roots)} bridge:Adapter entities; "
            "exactly one, the root entity, is expected"
        )
    root = roots[0]

    manifests = list(graph.objects(root, BRIDGE.testManifest))
    if len(manifests) != 1:
        raise SystemExit(
            f"  FAIL  the adapter names {len(manifests)} bridge:testManifest "
            "values; exactly one is expected"
        )
    manifest_iri = manifests[0]
    manifest_file = Path(url2pathname(urlparse(str(manifest_iri)).path))
    if not manifest_file.is_file():
        raise SystemExit(
            f"  FAIL  the adapter's bridge:testManifest names {manifest_file}, "
            "which does not exist"
        )
    graph.parse(manifest_file, format="turtle", publicID=str(manifest_iri))

    return Crate(adapter, graph, root, manifest_iri, manifest_file)


_loaded: dict[Path, Crate] = {}


def from_context(context):
    """The crate for the package a requirement is being run against.

    Parsed once per package per run: every requirement asks for it, and the
    parse is the expensive part.
    """
    uri = context.settings.rocrate_uri
    for candidate in (getattr(uri, "path", None), str(uri)):
        if not candidate:
            continue
        text = str(candidate)
        if text.startswith("file://"):
            text = text.removeprefix("file://").lstrip("/")
        path = Path(text)
        if path.is_dir():
            path = path.resolve()
            if path not in _loaded:
                _loaded[path] = load(path)
            return _loaded[path]
    raise FileNotFoundError(f"cannot read {uri} as a directory")
