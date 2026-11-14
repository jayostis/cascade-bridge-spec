from rdflib import Graph

from _terms import BRIDGE


def accounting_of(crate):
    """The graph of the one accounting the adapter names, empty where source_accounting.py has a fault to report."""
    named = list(crate.graph.objects(crate.root, BRIDGE.sourceAccounting))
    path = crate.file_at(named[0]) if len(named) == 1 else None
    if path is None:
        return Graph()
    try:
        return Graph().parse(path, format="turtle")
    except Exception:
        return Graph()
