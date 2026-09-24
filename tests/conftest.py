import pytest
from rdflib.plugins.sparql.algebra import translateQuery
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.plugins.sparql.processor import SPARQLProcessor


@pytest.fixture(scope="session", autouse=True)
def sparql_translated_once():
    """pyshacl hands rdflib each SPARQL constraint as text, which rdflib parses again on every run."""
    translated = {}
    query = SPARQLProcessor.query

    def once(self, text, initBindings=None, initNs=None, base=None, DEBUG=False):  # noqa: N803
        if isinstance(text, str):
            key = (text, base, tuple(sorted((initNs or {}).items())))
            if key not in translated:
                translated[key] = translateQuery(parseQuery(text), base, initNs or {})
            text = translated[key]
        return query(self, text, initBindings, initNs, base, DEBUG)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(SPARQLProcessor, "query", once)
        yield
