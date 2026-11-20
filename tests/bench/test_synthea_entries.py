import json

import synthea_entries

SMALL = "11111111-2222-3333-4444-555555555555"
LARGE = "66666666-7777-8888-9999-000000000000"


def bundle(entries):
    return json.dumps({"resourceType": "Bundle", "entry": [{"resource": {"resourceType": "Observation"}}] * entries})


class TestCountingTheEntriesOfEachSyntheaPerson:
    """Counting the entries of each Synthea person · bench/generate/synthea_entries.py

    Synthea writes one FHIR record for each person it invents, beside the hospitals' and practitioners' files, which
    are no person's.
    """

    def test_counts_the_entries_of_each_person_and_none_of_the_hospitals_or_practitioners(self, tmp_path, capsys):
        fhir = tmp_path / "fhir"
        fhir.mkdir()
        (fhir / f"Ada_Lovelace_{LARGE}.json").write_text(bundle(5), encoding="utf-8")
        (fhir / f"Alan_Turing_{SMALL}.json").write_text(bundle(2), encoding="utf-8")
        (fhir / "hospitalInformation1790812800000.json").write_text(bundle(9), encoding="utf-8")
        (fhir / "practitionerInformation1790812800000.json").write_text(bundle(9), encoding="utf-8")
        synthea_entries.main([str(tmp_path)])
        rows = [line.split() for line in capsys.readouterr().out.splitlines()[1:]]
        assert [(row[0], row[2]) for row in rows] == [("2", SMALL), ("5", LARGE)]
