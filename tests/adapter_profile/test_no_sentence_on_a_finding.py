from adapter_profile_world import ROOT

SEARCHED = ("shapes", "vocab", "adapter", "fixtures")


def test_no_file_under_the_shapes_the_vocabulary_the_adapter_or_the_fixtures_writes_an_oa_textual_body():
    written = [
        str(path.relative_to(ROOT)).replace("\\", "/")
        for directory in SEARCHED
        for path in sorted((ROOT / directory).rglob("*"))
        if path.is_file()
        and "__pycache__" not in path.parts
        and "TextualBody" in path.read_text(encoding="utf-8", errors="replace")
    ]
    assert written == []
