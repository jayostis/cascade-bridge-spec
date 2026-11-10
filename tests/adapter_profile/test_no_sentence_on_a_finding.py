from adapter_profile_world import ROOT

SEARCHED = ("shapes", "vocab", "adapter", "fixtures")


class TestTripwireNoSentenceWrittenOnAFinding:
    """Tripwire: no sentence written on a finding · shapes/, vocab/, adapter/, fixtures/"""

    class TestGivenEveryFileUnderShapesVocabAdapterAndFixtures:
        """given every file under `shapes/`, `vocab/`, `adapter/` and `fixtures/`"""

        def test_writes_no_oa_textualbody(self):
            """writes no `oa:TextualBody`"""
            written = [
                str(path.relative_to(ROOT)).replace("\\", "/")
                for directory in SEARCHED
                for path in sorted((ROOT / directory).rglob("*"))
                if path.is_file()
                and "__pycache__" not in path.parts
                and "TextualBody" in path.read_text(encoding="utf-8", errors="replace")
            ]
            assert written == []
