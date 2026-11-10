"""compatibility.json's form: what a run refuses before it picks anything."""

import json

import pytest

from compatibility_tool.console import Stop
from compatibility_tool.document import named_repositories, problems
from compatibility_world import CONTEXT_IRI, CRATE, VOCABULARY, engine_document

PICKED_WHEN_THE_CHECK_RUNS = "picked when the check runs"
ADAPTER = "https://github.com/jayostis/adapter"


def refused(directory, **document):
    return "\n".join(problems(directory, {"@context": CONTEXT_IRI, **engine_document([ADAPTER], **document)}))


class TestWhatARepositorysCompatibilityJsonMaySay:
    """What a repository's compatibility.json may say · compatibility.json, vocab/compatibility.context.jsonld

    An engine, an adapter, a runtime and a vocabulary each commit a `compatibility.json` naming what it must pass with
    and, for an engine or a runtime, its hosts. A file of no known form is refused before anything runs.
    """

    class TestGivenAnAdapterWithNoCompatibilityJson:
        """given an adapter with no `compatibility.json`"""

        def test_is_nothing_to_check_not_a_pass(self, world):
            """is nothing to check, not a pass"""
            adapter = world.clone("adapter")
            world.clone(VOCABULARY)
            said = world.tool(adapter)
            assert "lists no counterpart: nothing to check" in said
            assert "\nPASS\n" not in said

    class TestGivenAKeyTheContextDoesNotDefine:
        def test_is_refused_naming_it(self, world):
            """is refused, naming it"""
            engine = world.engine([world.url("adapter")], specVersion="v1-draft")
            said = world.tool(engine, 1)
            assert "specVersion is not a key the context defines" in said

    class TestGivenAnEntryWrittenAsAnObject:
        def test_is_refused_saying_the_version_is_picked_when_the_check_runs(self, tmp_path):
            """is refused, saying the version is picked when the check runs"""
            assert PICKED_WHEN_THE_CHECK_RUNS in refused(
                tmp_path, mustPassWith=[{"codeRepository": ADAPTER, "tag": "v1"}]
            )

    class TestGivenAFileOfNeitherForm:
        @pytest.mark.parametrize(
            "overrides, says",
            [
                pytest.param({"setup": None}, "carries setup and command", id="a host carrying no setup"),
                pytest.param({"command": None}, "carries setup and command", id="a host carrying no command"),
                pytest.param({"setup": "cargo build"}, "argument vector", id="an argument vector written as a string"),
                pytest.param(
                    {"mustPassWith": "https://example.org/x"}, "written as a JSON array", id="entries not a list"
                ),
            ],
        )
        def test_is_refused(self, tmp_path, overrides, says):
            assert says in refused(tmp_path, **overrides)

    class TestGivenAnEnginesFileNamingNoHost:
        """given an engine's file naming no host"""

        @pytest.mark.parametrize(
            "host",
            [pytest.param(None, id="no host key"), pytest.param([], id="an empty list of hosts")],
        )
        def test_is_refused_saying_an_engine_names_one(self, tmp_path, host):
            """is refused, saying an engine names one"""
            said = refused(tmp_path, host=host)
            assert "names at least one host" in said
            assert "not a key the context defines" not in said

    class TestGivenAnAdaptersFileCarryingSetupOrCommand:
        """given an adapter's file carrying setup or command"""

        def test_is_refused(self, tmp_path):
            (tmp_path / CRATE).write_text("{}", encoding="utf-8")
            document = {"@context": CONTEXT_IRI, "mustPassWith": [ADAPTER], "command": ["node", "cli.js"]}
            assert "an adapter's compatibility.json carries no" in "\n".join(problems(tmp_path, document))

    class TestGivenAFileWhoseContextIsNotTheSpecifications:
        """given a file whose context is not the specification's"""

        def test_is_refused(self, tmp_path):
            assert "its @context is" in "\n".join(problems(tmp_path, {"@context": "https://example.org/other"}))

    class TestGivenTwoCounterpartsWhoseRepositoriesShareAName:
        def test_is_refused(self, tmp_path):
            assert "at most once" in refused(tmp_path, mustPassWith=[ADAPTER, "https://example.org/elsewhere/adapter"])

    class TestGivenACounterpartNamedCascadeBridgeSpec:
        """given a counterpart named `cascade-bridge-spec`"""

        def test_is_refused(self, tmp_path):
            said = refused(tmp_path, mustPassWith=["https://github.com/jayostis/cascade-bridge-spec"])
            assert "No repository in mustPassWith is named cascade-bridge-spec" in said

    class TestGivenARuntimesFile:
        """given a runtime's file"""

        @pytest.mark.parametrize(
            "document, named, says",
            [
                pytest.param(
                    {"mustPassWith": [ADAPTER]}, ADAPTER, "names no mustPassWith", id="an adapter named, no runtime"
                ),
                pytest.param(
                    {"mustPassWith": None},
                    "https://github.com/jayostis/cascade-bridge-spec",
                    "is named cascade-bridge-spec",
                    id="a repository",
                ),
            ],
        )
        def test_is_refused_where_it_names_counterparts_or_a_repository_clashes(self, tmp_path, document, named, says):
            entry = {"repository": named}
            (tmp_path / "cascade-runtime.json").write_text(
                json.dumps({"vocabulary": entry, "adapters": []}), encoding="utf-8"
            )
            assert says in "\n".join(problems(tmp_path, {"@context": CONTEXT_IRI, **engine_document([], **document)}))

    class TestGivenARuntimesAdaptersWrittenAsAnObject:
        """given a runtime's adapters written as an object"""

        def test_stops_the_run(self, tmp_path):
            entry = {"repository": ADAPTER}
            (tmp_path / "cascade-runtime.json").write_text(
                json.dumps({"vocabulary": entry, "adapters": entry}), encoding="utf-8"
            )
            with pytest.raises(Stop, match="adapters"):
                named_repositories(tmp_path)

    class TestGivenAVocabularyNamingNoRuntime:
        @pytest.mark.parametrize(
            "must_pass_with", [None, []], ids=["no list of what it must pass with", "an empty list of it"]
        )
        def test_is_refused_so_an_adapter_typed_wrongly_is_not_passed(self, tmp_path, must_pass_with):
            """is refused, so an adapter typed wrongly is not passed"""
            (tmp_path / CRATE).write_text('{"@graph": [{"@id": "./", "@type": "Dataset"}]}', encoding="utf-8")
            document = (
                {"@context": CONTEXT_IRI} if must_pass_with is None else {"@context": CONTEXT_IRI, "mustPassWith": []}
            )
            assert "names a runtime in mustPassWith" in "\n".join(problems(tmp_path, document))
