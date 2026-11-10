import contextlib
import gzip
import io
import json

import pytest

import synthea_person

PERSON = "11111111-2222-3333-4444-555555555555"

HOSPITALS = {
    "resourceType": "Bundle",
    "entry": [
        {
            "resource": {
                "resourceType": "Organization",
                "name": "ACME CLINIC",
                "telecom": [{"system": "phone", "value": "(555) 867-5309"}, {"system": "email", "value": "a@b.c"}],
                "address": [{"line": ["12 REAL ROAD"], "city": "Springfield", "postalCode": "123456789"}],
            }
        },
        {"resource": {"resourceType": "Location", "name": "687", "address": {"line": ["9 FIELD LANE"]}}},
        {"resource": {"resourceType": "Organization", "name": "AT&T CLINIC"}},
    ],
}
PRACTITIONERS = {
    "resourceType": "Bundle",
    "entry": [
        {
            "resource": {
                "resourceType": "Practitioner",
                "name": [{"family": "Doe"}],
                "telecom": [{"system": "phone", "value": "555-111-2222"}],
                "address": [{"line": ["34 OTHER AVE"], "city": "Shelbyville", "postalCode": "98001"}],
            }
        }
    ],
}

FHIR = """{
  "resourceType": "Bundle",
  "type": "transaction",
  "entry": [ {
    "fullUrl": "urn:uuid:aaaaaaaa-3072-f687-8f6b-000000000001",
    "resource": {
      "resourceType": "Encounter",
      "serviceProvider": {
        "reference": "urn:uuid:aaaaaaaa-3072-f687-8f6b-000000000002",
        "display": "ACME CLINIC"
      },
      "location": [ {
        "location": {
          "display": "687"
        }
      } ]
    }
  }, {
    "fullUrl": "urn:uuid:aaaaaaaa-3072-f687-8f6b-000000000003",
    "resource": {
      "resourceType": "Practitioner",
      "name": [ {
        "family": "Doe"
      } ],
      "telecom": [ {
        "system": "phone",
        "value": "555-111-2222"
      } ],
      "address": [ {
        "line": [ "34 OTHER AVE", "Suite 687A" ],
        "city": "SHELBYVILLE",
        "postalCode": "98001"
      } ]
    }
  }, {
    "resource": {
      "resourceType": "Composition",
      "text": {
        "div": "<div>Seen at acme clinic, \\"AT&T Clinic\\".\\nCall (555) 867-5309 or ACME CLINICAL, 687.</div>"
      }
    }
  } ]
}
"""
FHIR_SCRUBBED = (
    FHIR.replace('"display": "ACME CLINIC"', '"display": "Bench Hospital"')
    .replace('"display": "687"', '"display": "Bench Hospital"')
    .replace('"value": "555-111-2222"', '"value": "555-0100"')
    .replace('"34 OTHER AVE"', '"1 Bench Street"')
    .replace('"city": "SHELBYVILLE"', '"city": "Bench City"')
    .replace(
        'Seen at acme clinic, \\"AT&T Clinic\\".\\nCall (555) 867-5309 or ACME CLINICAL, 687.',
        'Seen at Bench Hospital, \\"Bench Hospital\\".\\nCall 555-0100 or ACME CLINICAL, Bench Hospital.',
    )
)

CCDA = """<?xml version="1.0" encoding="UTF-8"?>
<ClinicalDocument>
  <id root="1.2.3" extension="x687y"/>
  <!-- written for ACME CLINIC -->
  <author>
    <representedOrganization displayName="AT&amp;T CLINIC">
      <name>ACME CLINIC</name>
      <telecom value="(555) 867-5309"/>
      <addr><streetAddressLine>12 REAL ROAD</streetAddressLine><city>Springfield</city><postalCode>123456789</postalCode></addr>
      <name>AT&amp;T CLINIC</name>
      <name>urn:uuid:aaaaaaaa-3072-f687-8f6b-000000000001</name>
    </representedOrganization>
  </author>
  <entry typeCode="DRIV"><act><text>Seen at ACME CLINIC and ACME CLINICAL</text></act></entry>
  <entry><act><id root="4.5" extension="687"/></act></entry>
</ClinicalDocument>
"""
CCDA_SCRUBBED = (
    CCDA.replace("written for ACME CLINIC", "written for Bench Hospital")
    .replace('displayName="AT&amp;T CLINIC"', 'displayName="Bench Hospital"')
    .replace("<name>ACME CLINIC</name>", "<name>Bench Hospital</name>")
    .replace('value="(555) 867-5309"', 'value="555-0100"')
    .replace("12 REAL ROAD", "1 Bench Street")
    .replace("<city>Springfield</city>", "<city>Bench City</city>")
    .replace("<postalCode>123456789</postalCode>", "<postalCode>000000000</postalCode>")
    .replace("<name>AT&amp;T CLINIC</name>", "<name>Bench Hospital</name>")
    .replace("Seen at ACME CLINIC and", "Seen at Bench Hospital and")
    .replace('extension="687"', 'extension="Bench Hospital"')
)


def synthea_folder(root, fhir=FHIR, ccda=CCDA):
    (root / "fhir").mkdir(parents=True)
    (root / "ccda").mkdir()
    (root / "fhir" / "hospitalInformation1790812800000.json").write_text(json.dumps(HOSPITALS), encoding="utf-8")
    (root / "fhir" / "practitionerInformation1790812800000.json").write_text(
        json.dumps(PRACTITIONERS), encoding="utf-8"
    )
    (root / "fhir" / f"Jane1_Doe2_{PERSON}.json").write_text(fhir, encoding="utf-8", newline="")
    (root / "ccda" / f"Jane1_Doe2_{PERSON}.xml").write_text(ccda, encoding="utf-8", newline="")
    return root


def made(folder, name):
    """The decompressed output and what `main()` printed, from one run over a fresh Synthea folder."""
    out = folder / name
    with contextlib.redirect_stdout(io.StringIO()) as printed:
        synthea_person.main([str(synthea_folder(folder / "synthea")), PERSON, str(out)])
    return gzip.decompress(out.read_bytes()).decode("utf-8"), printed.getvalue()


def unreadable_name(root):
    path = root / "fhir" / f"Jane1_Doe2_{PERSON}.json"
    path.write_text(FHIR.replace('"display": "ACME CLINIC"', '"display": "\\u0041CME CLINIC"'), encoding="utf-8")


def second_file(root):
    (root / "fhir" / f"Jane9_Doe9_{PERSON}.json").write_text(FHIR, encoding="utf-8")


def no_person(root):
    (root / "fhir" / f"Jane1_Doe2_{PERSON}.json").unlink()


def no_hospitals(root):
    (root / "fhir" / "hospitalInformation1790812800000.json").unlink()
    (root / "fhir" / "practitionerInformation1790812800000.json").unlink()


class TestMakingASyntheaPersonsRecordSafeToCommit:
    """Making a Synthea person's record safe to commit · bench/generate/synthea_person.py

    Synthea writes real hospitals' names, addresses and telephone numbers into the records it invents. Each such value
    is removed: replaced by a stand-in such as `Bench Hospital`, wherever it stands whole in a string, a text node or an
    attribute.
    """

    class TestGivenAPersonsFhirRecord:
        """given a person's FHIR record"""

        @pytest.fixture(scope="class")
        @classmethod
        def result(cls, tmp_path_factory):
            return made(tmp_path_factory.mktemp("fhir"), "record.json.gz")

        def test_replaces_each_removed_value_with_its_stand_in_and_keeps_every_other_byte(self, result):
            """replaces each removed value with its stand-in and keeps every other byte"""
            assert result[0] == FHIR_SCRUBBED

        def test_prints_how_many_entries_the_record_has(self, result):
            assert "entries 3" in result[1]

        def test_writes_the_same_bytes_on_two_runs(self, tmp_path):
            root = synthea_folder(tmp_path / "synthea")
            for name in ("first.json.gz", "second.json.gz"):
                synthea_person.main([str(root), PERSON, str(tmp_path / name)])
            assert (tmp_path / "first.json.gz").read_bytes() == (tmp_path / "second.json.gz").read_bytes()

    class TestGivenAPersonsCcdaDocument:
        """given a person's C-CDA document"""

        @pytest.fixture(scope="class")
        @classmethod
        def result(cls, tmp_path_factory):
            return made(tmp_path_factory.mktemp("ccda"), "record.xml.gz")

        def test_replaces_each_removed_value_with_its_stand_in_and_keeps_every_other_byte(self, result):
            """replaces each removed value with its stand-in and keeps every other byte"""
            assert result[0] == CCDA_SCRUBBED

        def test_prints_how_many_entries_the_document_has(self, result):
            assert "entries 2" in result[1]

    class TestGivenARecordItCannotMakeSafeOrCannotFind:
        @pytest.mark.parametrize(
            ("damage", "reason"),
            [
                pytest.param(
                    unreadable_name,
                    "removed values are left",
                    id="a removed value written in a form the scrub cannot see",
                ),
                pytest.param(second_file, "2 .json files", id="two files"),
                pytest.param(no_person, "0 .json files", id="no file"),
                pytest.param(no_hospitals, "no hospitalInformation", id="no provider files"),
            ],
        )
        def test_exits_with_the_reason_having_written_nothing(self, tmp_path, damage, reason):
            """exits with the reason, having written nothing"""
            root = synthea_folder(tmp_path / "synthea")
            damage(root)
            out = tmp_path / "record.json.gz"
            with pytest.raises(SystemExit, match=reason):
                synthea_person.main([str(root), PERSON, str(out)])
            assert not out.exists()

    class TestMain:
        """`main()`"""

        def test_exits_for_an_output_name_that_ends_in_neither_json_gz_nor_xml_gz(self, tmp_path):
            """exits for an output name that ends in neither `.json.gz` nor `.xml.gz`"""
            root = synthea_folder(tmp_path / "synthea")
            with pytest.raises(SystemExit):
                synthea_person.main([str(root), PERSON, str(tmp_path / "record.gz")])
