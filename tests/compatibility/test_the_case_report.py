"""The report of each case a run's engine hosts ran: `report.ctrf.json` for a tool, `report.md` for a person."""

import json
import re
import sys

import pytest
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDFS

from compatibility_tool.judge import judge_report
from compatibility_world import SYNTHETIC_ADAPTER, a_host, earl_report, engine_document, write_compatibility, writing

MF = Namespace("http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#")
MANIFEST = SYNTHETIC_ADAPTER / "fixtures" / "manifest.ttl"
LABEL = "synthetic adapter fixture cases"
NATIVE = "with engine on native"
PASSING = {
    "example-0001": "earl:passed",
    "example-0002": "earl:cantTell",
    "example-0002-and-example-0007-name-one-record": "earl:passed",
    "example-0003": "earl:passed",
    "example-0004": "earl:passed",
    "example-0005": "earl:passed",
    "example-0006": "earl:passed",
    "example-0008": "earl:passed",
    "example-0008-names-two-records": "earl:passed",
    "example-release-2026-01": "earl:untested",
}
FAILED_SENTENCE = "example-0001 is reported failed: a report that holds gives only passed, cantTell or untested"


def names_in_the_manifest():
    return {str(name) for name in Graph().parse(MANIFEST, format="turtle").objects(None, MF.name)}


def comment_in_the_manifest(name):
    graph = Graph().parse(MANIFEST, format="turtle")
    entry = next(graph.subjects(MF.name, Literal(name)))
    comment = graph.value(entry, RDFS.comment)
    return None if comment is None else str(comment)


def report_of(world):
    return json.loads((world.results / "report.ctrf.json").read_text(encoding="utf-8"))


def cases_of(world):
    return report_of(world)["results"]["tests"]


def case_named(world, name):
    (found,) = (case for case in cases_of(world) if case["name"] == name)
    return found


def faults_judged(world, host=1):
    report = world.results / "earl" / f"adapter-on-host-{host}.ttl"
    return judge_report(report, world.workspace / "adapter").faults


def manifest_address(world):
    return (world.workspace / "adapter" / "fixtures" / "manifest.ttl").resolve().as_uri()


def assertion(world, test, outcome):
    return (
        f"[] a earl:Assertion ; earl:test <{manifest_address(world)}#{test}> ; "
        f"earl:result [ a earl:TestResult ; earl:outcome earl:{outcome} ] .\n"
    )


def engine_writing(world, outcomes, more="", manifest=None):
    """An engine beside the adapter whose one host writes a report of these outcomes, whatever the adapter says.

    The report names the tests at the manifest's address, or at `manifest` where another is given.
    """
    engine = world.engine_beside_adapter()
    command = writing(world.root, earl_report(manifest or manifest_address(world), outcomes) + more)
    write_compatibility(engine, engine_document([world.url("adapter")], command=command))
    return engine


@pytest.fixture(scope="class")
def clean(shared_world):
    """An adapter run by the one host of an engine, and judged to hold in every case."""
    adapter = shared_world.adapter_beside_engine()
    shared_world.tool(adapter)
    return shared_world


class TestAReportOfEveryCaseAnEngineRan:
    """A report of every case an engine ran · report.ctrf.json, report.md

    A case is one entry of an adapter's test manifest, run on one engine host. A compatibility run that has an engine
    run the manifest writes each case's result into its results directory: `report.ctrf.json` for a tool, `report.md`
    for a person. A case fails here exactly when the judge finds a fault against it, so the report and the table
    never disagree.
    """

    class TestGivenAnAdapterWhoseEveryCaseTheEnginesOneHostJudgesWell:
        """given an adapter whose every case the engine's one host judges well"""

        def test_writes_both_files(self, clean):
            """writes `report.ctrf.json` and `report.md` into the results directory"""
            assert (clean.results / "report.md").is_file()
            report = report_of(clean)
            assert report["reportFormat"] == "CTRF"
            assert {"tool", "summary", "tests"} <= set(report["results"])

        def test_lists_each_entry_of_the_test_manifest_once(self, clean):
            names = [case["name"] for case in cases_of(clean)]

            assert sorted(names) == sorted(names_in_the_manifest())
            assert len(names) == len(set(names))

        def test_names_a_case_by_its_name_under_the_label_and_the_host(self, clean):
            """names a case by its `mf:name`, under the manifest's label and then `with engine on native`"""
            case = case_named(clean, "example-0001")

            assert case["suite"] == [LABEL, NATIVE]

        def test_gives_a_case_its_comment_as_its_description(self, clean):
            """gives a case its `rdfs:comment` as its description"""
            assert case_named(clean, "example-0003")["extra"]["description"] == comment_in_the_manifest("example-0003")
            assert "description" not in case_named(clean, "example-0001")["extra"]

        def test_gives_a_case_the_manifests_path_and_the_line_its_entry_begins_on(self, clean):
            """gives a case the manifest's path and the line its entry begins on"""
            lines = MANIFEST.read_text(encoding="utf-8").splitlines()
            begins = next(number for number, text in enumerate(lines, 1) if text.startswith("<#example-0003>"))

            case = case_named(clean, "example-0003")

            assert (case["filePath"], case["line"]) == ("fixtures/manifest.ttl", begins)

        def test_reports_passed_as_passed_cantTell_as_other_and_untested_as_skipped(self, clean):
            """reports `passed` as passed, `cantTell` as other and `untested` as skipped"""
            by_name = {name: case_named(clean, name) for name in PASSING}

            for name, outcome in PASSING.items():
                word = outcome.removeprefix("earl:")
                assert by_name[name]["extra"]["outcome"] == [word]
                assert by_name[name]["status"] == {"passed": "passed", "cantTell": "other", "untested": "skipped"}[word]

        def test_counts_the_cases_of_each_status_in_the_summary(self, clean):
            """counts the cases of each status in `summary`"""
            report = report_of(clean)["results"]
            summary, tests = report["summary"], report["tests"]

            assert summary["tests"] == len(tests) == 10
            for status in ("passed", "failed", "skipped", "other"):
                assert summary[status] == sum(case["status"] == status for case in tests)
            assert summary["pending"] == 0

        def test_gives_the_run_its_real_start_and_stop_around_the_hosts_runs(self, world):
            """gives `summary` the run's own `start` and `stop`, the host's run falling between them"""
            engine = engine_writing(world, PASSING)
            command = world.root / "write_report.py"
            ran = world.root / "host_ran_at"
            command.write_text(
                command.read_text(encoding="utf-8")
                + f"import time\npathlib.Path({str(ran)!r}).write_text(str(int(time.time() * 1000)))\n",
                encoding="utf-8",
            )

            world.tool(engine)

            summary = report_of(world)["results"]["summary"]
            assert summary["start"] <= int(ran.read_text()) <= summary["stop"]

        def test_gives_the_run_its_duration_as_the_stop_less_the_start(self, clean):
            """gives `summary.duration` as the milliseconds from `start` to `stop`"""
            summary = report_of(clean)["results"]["summary"]

            assert summary["duration"] == summary["stop"] - summary["start"]

        def test_marks_the_report_as_timing_no_case(self, clean):
            """marks the report as timing no case: `results.extra.caseDurations` is `unmeasured`, each case's `duration` being 0"""
            report = report_of(clean)

            assert report["results"]["extra"]["caseDurations"] == "unmeasured"
            assert {case["duration"] for case in cases_of(clean)} == {0}

        def test_names_the_adapters_repository_and_commit_on_each_case(self, clean):
            """names the adapter's repository and commit on each case"""
            adapter = clean.record()["repositories"]["adapter"]

            assert re.fullmatch(r"[0-9a-f]{40}", adapter["commit"])
            for case in cases_of(clean):
                assert case["extra"]["adapter"] == {"repository": adapter["repository"], "commit": adapter["commit"]}

    class TestGivenACaseTheJudgeHoldsAFaultAgainst:
        @pytest.mark.parametrize(
            ("how", "name"),
            [
                ("failed", "example-0001"),
                ("no outcome", "example-0003"),
                ("input-only passed", "example-0002"),
                ("not one of EARL's five", "example-0001"),
            ],
            ids=["failed", "no outcome", "input-only passed", "not one of EARL's five"],
        )
        def test_reports_the_case_failed_with_the_fault_as_its_message(self, world, how, name):
            """reports the case failed, with the fault as its message"""
            written = {
                "input-only passed": PASSING | {"example-0002": "earl:passed"},
                "not one of EARL's five": PASSING | {"example-0001": "earl:maybe"},
            }
            engine = (
                engine_writing(world, written[how])
                if how in written
                else world.engine_beside_adapter(canned="failed" if how == "failed" else "partial")
            )

            world.tool(engine, expected=1)

            fault = "; ".join(fault for fault in faults_judged(world) if name in fault.split(" is ")[0])
            assert fault
            case = case_named(world, name)
            assert (case["status"], case["message"]) == ("failed", fault)
            if how == "failed":
                assert fault == FAILED_SENTENCE
                assert case_named(world, "example-0003")["status"] == "passed"

        @pytest.mark.parametrize("how", ["a result naming no test", "a report recording no outcome"])
        def test_lists_a_fault_that_names_no_entry_as_a_failed_case_of_its_own(self, world, how):
            """lists a fault that names no entry as a failed case of its own, named by the fault"""
            outcomes = {} if how == "a report recording no outcome" else PASSING
            naming_no_test = (
                "[] earl:result [ earl:outcome earl:failed ] .\n" if how == "a result naming no test" else ""
            )
            engine = engine_writing(world, outcomes, naming_no_test)

            world.tool(engine, expected=1)

            (fault,) = [fault for fault in faults_judged(world) if " has no outcome" not in fault]
            (own,) = [case for case in cases_of(world) if case["name"] == fault]
            assert (own["status"], own["message"], own["suite"]) == ("failed", fault, [LABEL, NATIVE])
            if how == "a report recording no outcome":
                assert {case["message"] for case in cases_of(world)} == {fault}
                assert sum(case["status"] == "failed" for case in cases_of(world)) == 11

    class TestGivenAnEntryWhoseOutcomesDiffer:
        """given an entry the report gives more than one outcome

        One status where every outcome agrees, and `other` where they do not.
        """

        @pytest.mark.parametrize(
            ("words", "status"),
            [(["passed", "untested"], "other"), (["cantTell", "passed"], "other"), (["passed", "passed"], "passed")],
            ids=["passed and untested", "cantTell and passed", "passed twice"],
        )
        def test_reports_other_unless_every_outcome_agrees(self, world, words, status):
            """reports `other` unless every outcome agrees, and lists the outcomes in `extra.outcome` in report order"""
            outcomes = PASSING | {"example-0001": f"earl:{words[0]}"}
            more = "".join(assertion(world, "example-0001", word) for word in words[1:])
            engine = engine_writing(world, outcomes, more)

            world.tool(engine)

            case = case_named(world, "example-0001")
            assert case["status"] == status
            assert case["extra"]["outcome"] == list(dict.fromkeys(words))
            assert "message" not in case

    class TestGivenAReportWhoseTestsAreNamedUnderAnotherAddress:
        """given a report that names the tests at an address other than the manifest's

        A report written where the adapter was checked out elsewhere: each test is matched to its entry by its path.
        """

        def test_matches_each_test_to_its_entry_by_the_path_within_the_adapter(self, world):
            outcomes = PASSING | {"example-0001": "earl:failed"}
            engine = engine_writing(world, outcomes, manifest="file:///elsewhere/adapter/fixtures/manifest.ttl")

            world.tool(engine, expected=1)

            assert case_named(world, "example-0001")["status"] == "failed"
            assert case_named(world, "example-0001")["message"] == FAILED_SENTENCE
            assert case_named(world, "example-0003")["status"] == "passed"
            assert case_named(world, "example-0002")["status"] == "other"

    class TestGivenAHostWhoseReportCannotBeJudged:
        """given a host whose report cannot be judged

        The engine ran, or could not, and left nothing the judge can read: the table's row says why, and each case
        says the same.
        """

        @pytest.mark.parametrize("how", ["no report", "not Turtle", "setup failed"])
        def test_reports_every_case_on_that_host_failed_with_what_the_table_says_of_the_host(self, world, how):
            overrides = {
                "no report": {"canned": "none"},
                "not Turtle": {"canned": "garbled"},
                "setup failed": {"setup": [sys.executable, "-c", "raise SystemExit(1)"]},
            }[how]
            engine = world.engine_beside_adapter(**overrides)

            world.tool(engine, expected=1)

            said = world.record()["repositories"]["adapter"]["result"]
            assert said
            assert len(cases_of(world)) == 10
            assert {(case["status"], case["message"]) for case in cases_of(world)} == {("failed", said)}

    class TestGivenAnEngineWithTwoHosts:
        def test_lists_every_case_under_each_hosts_own_level(self, world):
            """lists every case under each host's own `with engine on …`"""
            engine = world.engine_beside_adapter(host=[a_host("native"), a_host("second")])

            world.tool(engine)

            levels = [case["suite"][1] for case in cases_of(world)]
            assert set(levels) == {NATIVE, "with engine on second"}
            assert levels.count(NATIVE) == levels.count("with engine on second") == 10

    class TestGivenAnAdapterWhoseTestManifestCannotBeRead:
        def test_reports_one_failed_case_that_names_the_manifest_and_says_why(self, world):
            engine = world.engine_beside_adapter()
            (world.workspace / "adapter" / "fixtures" / "manifest.ttl").write_text("not turtle {\n", encoding="utf-8")

            world.tool(engine, expected=1)

            (case,) = cases_of(world)
            assert case["name"] == "the adapter's test manifest"
            assert case["status"] == "failed"
            assert case["message"].startswith("the adapter's test manifest could not be read:")
            assert case["suite"] == ["adapter", NATIVE]
            description = case["extra"]["levels"][0]["description"]
            assert "could not be read" in description
            assert "0 cases" not in description

    class TestGivenAFaultNamingNoEntry:
        def test_counts_its_case_in_the_manifests_description(self, world):
            engine = engine_writing(world, PASSING, "[] earl:result [ earl:outcome earl:failed ] .\n")

            world.tool(engine, expected=1)

            assert len(cases_of(world)) == 11
            assert case_named(world, "example-0001")["extra"]["levels"][0]["description"].startswith("11 cases")

    class TestGivenARunInWhichNoEngineRunsAnAdapter:
        """given a run in which no engine runs an adapter

        A runtime's or a vocabulary's run is judged by the conformance report, which has its own page; a run that
        stops before the engines has nothing case by case to say.
        """

        @pytest.mark.parametrize("how", ["a runtime's run", "a run that checks out only", "a refused file"])
        def test_writes_neither_file(self, world, how):
            if how == "a runtime's run":
                runtime, ci = world.runtime_under_test()
                world.tool(runtime, **ci)
            elif how == "a run that checks out only":
                world.tool(world.engine_beside_adapter(), checkout_only=True)
            else:
                world.tool(world.engine_beside_adapter(bogus=1), expected=1)

            assert not (world.results / "report.ctrf.json").exists()
            assert not (world.results / "report.md").exists()

        def test_removes_the_report_an_earlier_run_left_in_the_results_directory(self, world):
            world.results.mkdir()
            for name in ("report.ctrf.json", "report.md"):
                (world.results / name).write_text("left by an earlier run\n", encoding="utf-8")

            world.tool(world.engine_beside_adapter(), checkout_only=True)

            assert not (world.results / "report.ctrf.json").exists()
            assert not (world.results / "report.md").exists()

    class TestReportMd:
        """`report.md`"""

        @pytest.fixture(scope="class")
        @classmethod
        def written(cls, shared_world):
            """One engine with a clean host listed first and a failing one second."""
            engine = shared_world.engine_beside_adapter(
                host=[a_host("second", canned="passed"), a_host("native", canned="failed")]
            )
            shared_world.tool(engine, expected=1)
            return (shared_world.results / "report.md").read_text(encoding="utf-8"), shared_world

        def test_puts_a_group_that_holds_a_failed_case_first_and_open(self, written):
            text, _ = written
            opening = re.search(r"<details[^>]*>\s*<summary>(.*?)</summary>", text, re.DOTALL)

            assert opening.group(0).startswith("<details open>")
            assert NATIVE in opening.group(1)

        def test_closes_a_group_that_holds_no_failed_case(self, written):
            text, _ = written
            closed = [opening for opening in re.findall(r"<details[^>]*>\s*<summary>.*?</summary>", text, re.DOTALL)]

            assert len(closed) == 2
            assert "open" not in closed[1].split("<summary>")[0]
            assert "with engine on second" in closed[1]

        def test_says_a_failed_cases_fault_beside_its_name(self, written):
            """says a failed case's fault beside its name"""
            text, _ = written

            (line,) = [line for line in text.splitlines() if "`example-0001`" in line and FAILED_SENTENCE in line]
            assert line

        def test_holds_no_markdown_table(self, written):
            """holds no Markdown table"""
            text, _ = written

            assert not [line for line in text.splitlines() if line.lstrip().startswith("|")]

    class TestGivenARunInCI:
        """given a run in CI"""

        @pytest.fixture(scope="class")
        @classmethod
        def ran(cls, shared_world):
            engine, event = shared_world.engine_under_test()
            variables = {
                **shared_world.ci(event=event),
                "CASCADE_REPORT_ARTIFACT": "report-engine",
                "GITHUB_RUN_ID": "77",
            }
            shared_world.tool(engine, **variables)
            return shared_world

        def test_appends_report_md_to_the_runs_summary_page_after_the_table(self, ran):
            """appends `report.md` to the run's summary page, after the table"""
            table = ran.table_in_results().splitlines()[0]
            heading = (ran.results / "report.md").read_text(encoding="utf-8").splitlines()[0]
            summary = ran.table()

            assert 0 <= summary.index(table) < summary.index(heading)

        def test_names_the_run_in_the_environment(self, ran):
            """names the run in `environment.buildUrl`"""
            environment = report_of(ran)["results"]["environment"]
            under_test = ran.record()["repositories"]["engine"]

            assert environment["buildUrl"].endswith("/actions/runs/77")
            assert environment["repositoryUrl"] == under_test["repository"]
            assert environment["commit"] == under_test["commit"]

        def test_says_in_table_md_where_the_runs_summary_is_and_which_artifact_holds_the_report(self, ran):
            """says in `table.md` where the run's summary is and which artifact holds `report.ctrf.json`"""
            table = ran.table_in_results()

            (line,) = [line for line in table.splitlines() if "/actions/runs/77" in line]
            assert "`report-engine`" in line
            assert "`report.ctrf.json`" in line
            assert table.index("| repository |") < table.index(line)

        def test_leaves_the_artifact_out_when_the_action_named_none(self, world):
            engine, event = world.engine_under_test()
            variables = {**world.ci(event=event), "GITHUB_RUN_ID": "77"}

            world.tool(engine, **variables)

            (line,) = [line for line in world.table_in_results().splitlines() if "/actions/runs/77" in line]
            assert "report.ctrf.json" not in line

        def test_says_nothing_of_a_report_in_table_md_when_the_run_wrote_none(self, world):
            """says nothing of a report in `table.md` when the run wrote none"""
            runtime, ci = world.runtime_under_test()

            world.tool(runtime, **ci, CASCADE_REPORT_ARTIFACT="report-runtime", GITHUB_RUN_ID="77")

            assert world.table_in_results()
            assert "report.ctrf.json" not in world.table_in_results()
            assert "/actions/runs/77" not in world.table_in_results()
