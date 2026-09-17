from rdflib import Literal, URIRef

import digests
from _terms import SCHEMA

INPUT_SET = "fixtures/in/example-0001.xml"
INPUT_RECORD = "fixtures/in/example-0002.xml"


def entity(crate, relative):
    return URIRef((crate.adapter / relative).resolve().as_uri())


def test_blames_the_crate_when_the_local_sha256_is_not_the_files(crate):
    crate.graph.set((entity(crate, INPUT_SET), SCHEMA.sha256, Literal("0" * 64)))
    found = "\n".join(digests.mismatches(crate))
    assert "the crate's sha256 is not this file's" in found
    assert "it is wrong about the file beside it" in found


def test_blames_this_copy_when_the_publishers_digest_disagrees(crate):
    record = entity(crate, INPUT_RECORD)
    md5 = next(p for p in crate.graph.predicates(record) if str(p).endswith("md5"))
    crate.graph.set((record, md5, Literal("0" * 32)))
    found = "\n".join(digests.mismatches(crate))
    assert "the publisher's md5 is not this copy's" in found
    assert "A different finding from a wrong sha256" in found


def test_never_compares_a_digest_on_bytes_that_are_not_committed(crate):
    committed = {path for path, _, _, _ in digests.claims(crate)}
    assert committed, "the fixture records digests on committed files"
    assert all(path.is_file() for path in committed)
