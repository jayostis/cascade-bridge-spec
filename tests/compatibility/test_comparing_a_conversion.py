"""What a conversion's graph is compared on: everything but the Bridge's release."""

from rdflib import Graph

from compatibility_tool import library

PREFIXES = """
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix cascade: <https://ns.cascadeprotocol.org/cascade#> .
"""


def converted(release, author):
    return Graph().parse(
        data=PREFIXES
        + f"""
_:doc prov:wasGeneratedBy _:writing ; prov:wasAttributedTo _:author .
_:writing prov:qualifiedAssociation [ prov:agent _:author ; prov:hadRole cascade:AuthorRole ] .
_:author rdfs:label "{author}" .
_:import prov:qualifiedAssociation [ prov:hadPlan [ a prov:Plan ] ; prov:agent _:release ] .
_:release rdfs:label "{release}" .
""",
        format="turtle",
    )


def test_a_release_named_differently_still_compares_equal():
    one, other = converted("release 1", "Registry"), converted("release 2", "Registry")

    assert library.isomorphic(library.without_release(one), library.without_release(other))


def test_an_author_named_differently_does_not_compare_equal():
    one, other = converted("release 1", "Registry"), converted("release 1", "Elsewhere")

    assert not library.isomorphic(library.without_release(one), library.without_release(other))
