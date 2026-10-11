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


def test_a_factor_of_three_gives_six_entries_and_leaves_the_text_around_them_alone():
    repeated = repeat_entries.repeat_entries(DOCUMENT, 3)
    assert len(ENTRY.findall(repeated)) == 6
    assert ENTRY.sub("", repeated).replace("\n", "") == ENTRY.sub("", DOCUMENT).replace("\n", "")


def test_an_id_with_a_root_gets_the_copy_and_a_counter_over_the_document_and_a_null_flavoured_one_none():
    repeated = repeat_entries.repeat_entries(DOCUMENT, 2)
    assert GENERATED.findall(repeated) == ["gen-0-0", "gen-0-1", "gen-1-2", "gen-1-3", "gen-0-4", "gen-1-5"]
    assert repeated.count('<id nullFlavor="NI"/>') == 2
    assert "old" not in repeated


def test_a_gz_output_holds_the_document_and_two_runs_write_the_same_bytes(tmp_path):
    source = tmp_path / "in.xml"
    source.write_text(DOCUMENT, encoding="utf-8", newline="")
    written = []
    for name in ("first.xml.gz", "second.xml.gz"):
        repeat_entries.main([str(source), "3", str(tmp_path / name)])
        written.append((tmp_path / name).read_bytes())
    assert written[0] == written[1]
    assert gzip.decompress(written[0]).decode("utf-8") == repeat_entries.repeat_entries(DOCUMENT, 3)


def test_a_factor_below_one_is_refused(tmp_path):
    with pytest.raises(SystemExit):
        repeat_entries.main([str(tmp_path / "in.xml"), "0", str(tmp_path / "out.xml")])
