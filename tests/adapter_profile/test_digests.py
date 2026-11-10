from rdflib import Literal, URIRef

import digests
from _terms import SCHEMA

INPUT_SET = "fixtures/in/example-0001.xml"
INPUT_RECORD = "fixtures/in/example-0002.xml"


def entity(crate, relative):
    return URIRef((crate.adapter / relative).resolve().as_uri())


class TestDigestsACrateRecords:
    """Digests a crate records · adapter/profile/must/digests.py

    A crate records a `sha256` of each committed file and may record the digest a publisher gave for an input. The two
    failures mean different things, and the report says which.
    """

    class TestGivenASha256ThatIsNotTheFiles:
        """given a `sha256` that is not the file's"""

        def test_blames_the_crate(self, crate):
            crate.graph.set((entity(crate, INPUT_SET), SCHEMA.sha256, Literal("0" * 64)))
            found = "\n".join(digests.mismatches(crate))
            assert "the crate's sha256 is not this file's" in found
            assert "it is wrong about the file beside it" in found

    class TestGivenAPublishersDigestThatDisagrees:
        """given a publisher's digest that disagrees"""

        def test_blames_this_copy_of_the_file(self, crate):
            record = entity(crate, INPUT_RECORD)
            md5 = next(p for p in crate.graph.predicates(record) if str(p).endswith("md5"))
            crate.graph.set((record, md5, Literal("0" * 32)))
            found = "\n".join(digests.mismatches(crate))
            assert "the publisher's md5 is not this copy's" in found
            assert "A different finding from a wrong sha256" in found

    class TestGivenADigestRecordedOnAFileThatIsNotThere:
        def test_reports_it_without_comparing_it(self, crate):
            crate.graph.set((entity(crate, "fixtures/in/not-there.xml"), SCHEMA.sha256, Literal("0" * 64)))
            found = "\n".join(digests.mismatches(crate))
            assert "not-there.xml: the crate records a crate's sha256 for a file that is not there" in found
            assert "is not this file's" not in found

    class TestGivenTheCrateOfTheSyntheticAdapter:
        def test_records_no_digest_on_a_file_that_is_not_there(self, crate):
            committed = {path for path, _, _, _ in digests.claims(crate)}
            assert committed, "the fixture records digests on committed files"
            assert all(path.is_file() for path in committed)
