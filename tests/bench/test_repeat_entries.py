import gzip
import re

import pytest

import repeat_entries

DOCUMENT = (
    '<ClinicalDocument>\n<id root="1.2.3" extension="document"/>\n'
    '<entry typeCode="DRIV"><act><id root="1.1"/><id root="1.2" extension="old"/><id nullFlavor="NI"/></act></entry>\n'
    '<entry>\n  <observation><id root="2.1"/></observation>\n</entry>\n'
    "</ClinicalDocument>\n"
)
ENTRY = re.compile(r"<entry[ >][\s\S]*?</entry>")
GENERATED = re.compile(r'<id root="[^"]*" extension="(gen-\d+-\d+)"')


class TestRepeatingADocumentsEntriesForABenchmarkInput:
    """Repeating a document's entries for a benchmark input · bench/generate/repeat_entries.py

    A larger benchmark input is made from a real-sized document by writing each of its entries several times, each copy
    with ids of its own.
    """

    class TestRepeatEntries:
        """`repeat_entries()`"""

        def test_writes_each_entry_as_many_times_as_the_factor(self):
            assert len(ENTRY.findall(repeat_entries.repeat_entries(DOCUMENT, 3))) == 6

        def test_leaves_every_character_outside_the_entries_as_it_was_line_feeds_apart(self):
            """leaves every character outside the entries as it was, line feeds apart

            Each copy is followed by a line feed, and the comparison drops line feeds on both sides.
            """
            repeated = repeat_entries.repeat_entries(DOCUMENT, 3)
            assert ENTRY.sub("", repeated).replace("\n", "") == ENTRY.sub("", DOCUMENT).replace("\n", "")

        def test_numbers_each_id_that_has_a_root_counting_through_the_document(self):
            """numbers each `id` that has a root `gen-<copy>-<count>`, counting through the document"""
            repeated = repeat_entries.repeat_entries(DOCUMENT, 2)
            assert GENERATED.findall(repeated) == ["gen-0-0", "gen-0-1", "gen-1-2", "gen-1-3", "gen-0-4", "gen-1-5"]

        def test_replaces_the_extension_such_an_id_had(self):
            """replaces the extension such an `id` had"""
            assert "old" not in repeat_entries.repeat_entries(DOCUMENT, 2)

        def test_leaves_an_id_with_no_root_as_it_was_once_in_each_copy(self):
            """leaves an `id` with no root as it was, once in each copy"""
            assert repeat_entries.repeat_entries(DOCUMENT, 2).count('<id nullFlavor="NI"/>') == 2

    class TestMain:
        """`main()`"""

        @pytest.fixture(scope="class")
        @classmethod
        def written(cls, tmp_path_factory):
            folder = tmp_path_factory.mktemp("repeat")
            source = folder / "in.xml"
            source.write_text(DOCUMENT, encoding="utf-8", newline="")
            written = []
            for name in ("first.xml.gz", "second.xml.gz"):
                repeat_entries.main([str(source), "3", str(folder / name)])
                written.append((folder / name).read_bytes())
            return written

        def test_writes_the_same_bytes_on_two_runs(self, written):
            assert written[0] == written[1]

        def test_holds_the_repeated_document_in_the_gz_it_writes(self, written):
            """holds the repeated document in the `.gz` it writes"""
            assert gzip.decompress(written[0]).decode("utf-8") == repeat_entries.repeat_entries(DOCUMENT, 3)

        def test_exits_for_a_factor_below_one(self, tmp_path):
            with pytest.raises(SystemExit):
                repeat_entries.main([str(tmp_path / "in.xml"), "0", str(tmp_path / "out.xml")])
