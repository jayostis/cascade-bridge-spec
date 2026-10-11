import gzip
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
                "address": [{"line": ["12 REAL ROAD"], "city": "Springfield"}],
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
                "address": [{"line": ["34 OTHER AVE"]}],
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
        "line": [ "34 OTHER AVE", "Suite 687A" ]
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
      <addr><streetAddressLine>12 REAL ROAD</streetAddressLine><city>Springfield</city></addr>
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


def written(tmp_path, name, root):
    out = tmp_path / name
    synthea_person.main([str(root), PERSON, str(out)])
    return gzip.decompress(out.read_bytes()).decode("utf-8")


def test_a_fhir_record_loses_each_removed_value_as_a_whole_and_keeps_every_other_byte(tmp_path, capsys):
    root = synthea_folder(tmp_path / "synthea")
    assert written(tmp_path, "record.json.gz", root) == FHIR_SCRUBBED
    assert "entries 3" in capsys.readouterr().out


def test_a_ccda_loses_each_removed_value_as_a_whole_text_node_or_attribute_and_keeps_every_other_byte(tmp_path, capsys):
    root = synthea_folder(tmp_path / "synthea")
    assert written(tmp_path, "record.xml.gz", root) == CCDA_SCRUBBED
    assert "entries 2" in capsys.readouterr().out


def test_two_runs_write_the_same_bytes(tmp_path):
    root = synthea_folder(tmp_path / "synthea")
    for name in ("first.json.gz", "second.json.gz"):
        synthea_person.main([str(root), PERSON, str(tmp_path / name)])
    assert (tmp_path / "first.json.gz").read_bytes() == (tmp_path / "second.json.gz").read_bytes()


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


@pytest.mark.parametrize(
    "damage",
    [unreadable_name, second_file, no_person, no_hospitals],
    ids=["a removed value written in a form the scrub cannot see", "two files", "no file", "no provider files"],
)
def test_a_record_it_cannot_make_safe_or_find_is_refused_and_nothing_is_written(tmp_path, damage):
    root = synthea_folder(tmp_path / "synthea")
    damage(root)
    out = tmp_path / "record.json.gz"
    with pytest.raises(SystemExit):
        synthea_person.main([str(root), PERSON, str(out)])
    assert not out.exists()


def test_an_output_name_that_is_neither_json_nor_xml_gz_is_refused(tmp_path):
    root = synthea_folder(tmp_path / "synthea")
    with pytest.raises(SystemExit):
        synthea_person.main([str(root), PERSON, str(tmp_path / "record.gz")])
