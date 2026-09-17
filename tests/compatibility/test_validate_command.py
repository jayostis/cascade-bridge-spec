import pytest
from compatibility_world import read_compatibility, write_compatibility

A_FILE_OF_NEITHER_FORM = (
    "A compatibility.json is an engine's, carrying exactly one specPin, "
    "one setup and one command, or an adapter's, carrying none of the three."
)


def engine_on_main(world):
    return world.engine(world.adapter_pin(branch="main"))


def adapter_naming_engine(world):
    adapter = world.clone("adapter")
    write_compatibility(adapter, {"mustPassWith": [{"codeRepository": world.url("engine"), "branch": "main"}]})
    return adapter


def test_validate_passes_an_engines_file_in_an_engines_directory(world):
    said = world.tool(engine_on_main(world), ("validate", 0))
    assert "the form is an engine's, as the directory is" in said
    assert "PASS" in said


def test_validate_passes_an_adapters_file_in_an_adapters_directory(world):
    said = world.tool(adapter_naming_engine(world), ("validate", 0))
    assert "the form is an adapter's, as the directory is" in said
    assert "PASS" in said


def test_validate_reports_nothing_to_check_not_a_pass_for_an_adapter_with_no_compatibility_json(world):
    said = world.tool(world.clone("adapter"), ("validate", 0))
    assert "has no compatibility.json: nothing to check" in said
    assert "validate: nothing to check" in said
    assert "\nPASS\n" not in said


def two_pin_kinds(world):
    return world.engine(world.adapter_pin(branch="main", tag="v1"))


def spec_pin_naming_two_pin_kinds(world):
    return world.engine([], specPin=dict(world.spec_pin(), branch="main"))


def spec_pin_without_code_repository(world):
    return world.engine([], specPin={"commit": world.commits["specification"]})


def engine_without_command(world):
    return world.engine(world.adapter_pin(branch="main"), command=None)


def engine_carrying_only_spec_pin(world):
    return world.engine(None, setup=None, command=None)


def adapter_carrying_spec_pin(world):
    adapter = adapter_naming_engine(world)
    write_compatibility(adapter, dict(read_compatibility(adapter), specPin=world.spec_pin()))
    return adapter


def engine_form_in_adapter(world):
    adapter = world.clone("adapter")
    write_compatibility(adapter, world.engine_file([]))
    return adapter


def misspelt_key(world):
    engine = engine_on_main(world)
    document = read_compatibility(engine)
    document["mustpasswith"] = document.pop("mustPassWith")
    write_compatibility(engine, document)
    return engine


def string_vector(world):
    return world.engine([], setup="npm ci")


def must_pass_with_object(world):
    return world.engine(world.adapter_pin(branch="main")[0])


def must_pass_with_number(world):
    return world.engine(5)


def spec_pin_array(world):
    return world.engine([], specPin=[world.spec_pin()])


def two_of_one_name(second):
    def build(world):
        return world.engine([*world.adapter_pin(branch="main"), {"codeRepository": second(world), "branch": "main"}])

    return build


def counterpart_at(*parts):
    def build(world):
        return world.engine([{"codeRepository": world.origins.joinpath(*parts).as_uri(), "branch": "main"}])

    return build


@pytest.mark.parametrize(
    "build, says",
    [
        pytest.param(
            two_pin_kinds, "A pin names exactly one of commit, tag or branch.",
            id="validate fails a pin naming two of commit, tag and branch",
        ),
        pytest.param(
            spec_pin_naming_two_pin_kinds, "A pin names exactly one of commit, tag or branch.",
            id="validate fails an engine's specPin naming two of commit, tag and branch",
        ),
        pytest.param(
            spec_pin_without_code_repository,
            "A pin names exactly one codeRepository, the repository's absolute URL.",
            id="validate fails an engine's specPin without codeRepository",
        ),
        pytest.param(
            engine_without_command, A_FILE_OF_NEITHER_FORM,
            id="validate fails an engine's file without command",
        ),
        pytest.param(
            engine_carrying_only_spec_pin, A_FILE_OF_NEITHER_FORM,
            id="validate fails an engine's file carrying only specPin",
        ),
        pytest.param(
            adapter_carrying_spec_pin, A_FILE_OF_NEITHER_FORM,
            id="validate fails an adapter's file carrying specPin",
        ),
        pytest.param(
            engine_form_in_adapter,
            "so it is an adapter, and an adapter's compatibility.json carries no specPin, setup, command",
            id="validate fails an engine's file in an adapter's directory",
        ),
        pytest.param(
            misspelt_key, "mustpasswith is not a key the context defines",
            id="validate fails a key the context does not define",
        ),
        pytest.param(
            string_vector, "setup is an argument vector, written as a JSON array of strings",
            id="validate fails an argument vector written as a string",
        ),
        pytest.param(
            must_pass_with_object, "mustPassWith is a list of pins, written as a JSON array",
            id="validate fails mustPassWith written as one object",
        ),
        pytest.param(
            must_pass_with_number, "mustPassWith is a list of pins, written as a JSON array",
            id="validate fails mustPassWith written as a number, in a sentence not a traceback",
        ),
        pytest.param(
            spec_pin_array, "specPin is one pin, written as a JSON object",
            id="validate fails specPin written as an array",
        ),
        pytest.param(
            two_of_one_name(lambda world: (world.origins / "fork" / "Adapter").as_uri()),
            "Each repository name appears in mustPassWith at most once",
            id="validate fails two counterparts whose names differ only in case",
        ),
        pytest.param(
            two_of_one_name(lambda world: world.url("adapter") + ".git"),
            "Each repository name appears in mustPassWith at most once",
            id="validate fails one counterpart listed with and without .git",
        ),
        pytest.param(
            counterpart_at("cascade-bridge-spec"),
            "No repository in mustPassWith is named cascade-bridge-spec",
            id="validate fails a counterpart named cascade-bridge-spec",
        ),
        pytest.param(
            counterpart_at("elsewhere", "engine"),
            "No repository in mustPassWith is named engine",
            id="validate fails a counterpart named as the repository under test",
        ),
    ],
)
def test_validate_fails_in_a_sentence(world, build, says):
    said = world.tool(build(world), ("validate", 1))
    assert says in said
    assert "validate: FAIL" in said
    assert "Traceback" not in said
