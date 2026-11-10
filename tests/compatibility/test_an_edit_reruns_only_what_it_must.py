import time

import pytest

from edited import decide
from rerun import Unread, rerun_when_edited

URL = "https://github.com/o/r/pull/1"
LINE = f"Depends-On: {URL}"
OTHER = "Depends-On: https://github.com/o/r/pull/2"
LINES = ["the Depends-On: lines changed"]
BASE = ["the base changed"]


def edit(description, head_repository="o/r", **changes):
    return {
        "action": "edited",
        "changes": changes,
        "pull_request": {
            "number": 7,
            "body": description,
            "head": {"sha": "h1", "repo": {"full_name": head_repository}},
        },
    }


def body_edit(before, after, head_repository="o/r", **more):
    return edit(after, head_repository, body={"from": before}, **more)


DECISIONS = {
    "a title only": (edit("x", title={"from": "old"}), []),
    "prose": (body_edit("a", "b"), []),
    "a line added to an empty description": (body_edit("", LINE), LINES),
    "a line added to a null description": (body_edit(None, LINE), LINES),
    "a line added after prose": (body_edit("intro", f"intro\n{LINE}"), LINES),
    "a line cut": (body_edit(f"intro\n{LINE}", "intro"), LINES),
    "a line cut, leaving a null description": (body_edit(LINE, None), LINES),
    "two lines reordered": (body_edit(f"{LINE}\n{OTHER}", f"{OTHER}\n{LINE}"), LINES),
    "the keyword's case and the whitespace around a line": (body_edit(LINE, f"  depends-on:   {URL}  "), []),
    "the case of the URL": (body_edit(LINE, LINE.replace("/o/", "/O/")), LINES),
    "a malformed line added": (body_edit("", "Depends-On: nonsense"), LINES),
    "a retarget": (edit("x", base={"ref": {"from": "main"}, "sha": {"from": "abc"}}), BASE),
    "a retarget and a line": (body_edit("", LINE, base={"ref": {"from": "main"}}), BASE + LINES),
    "not an edit": ({"action": "synchronize", "pull_request": edit("x")["pull_request"]}, []),
}


def run(identifier=1, status="completed", attempt=1, number=7, head="h1", **more):
    return {
        "id": identifier,
        "run_number": identifier,
        "status": status,
        "run_attempt": attempt,
        "head_sha": head,
        "pull_requests": [{"number": number}],
        "head_repository": {"full_name": "o/r"},
        **more,
    }


def finish(status):
    def hook(found):
        found["status"] = "completed"
        return status

    return hook


def ignore(status):
    return lambda found: status


def restart(status):
    def hook(found):
        found["run_attempt"] += 1
        found["status"] = "queued"
        return status

    return hook


def refuse_once_after_another_edit():
    asked = []

    def hook(found):
        asked.append(found["id"])
        if len(asked) > 1:
            return restart(201)(found)
        found["run_attempt"] += 1
        found["status"] = "in_progress"
        return 403

    return hook


class Fake:
    def __init__(self, runs, heads=("h1",), cancel=None, force=None, rerun=None, forbid=None):
        self.runs = {found["id"]: found for found in runs}
        self.heads = list(heads)
        self.forbid = forbid
        self.calls = []
        self.hooks = {
            "cancel": cancel or finish(202),
            "force-cancel": force or finish(202),
            "rerun": rerun or restart(201),
        }

    def get(self, path):
        if self.forbid and self.forbid in path:
            raise Unread(f"GET {path} answered 403")
        if "/pulls/" in path:
            return {"head": {"sha": self.heads.pop(0) if len(self.heads) > 1 else self.heads[0]}}
        if "/workflows/" in path:
            head = path.split("head_sha=")[1].split("&")[0]
            return {"workflow_runs": [dict(found) for found in self.runs.values() if found["head_sha"] == head]}
        return dict(self.runs[int(path.rsplit("/", 1)[1])])

    def post(self, path):
        *_, identifier, verb = path.split("/")
        self.calls.append(f"{verb} {identifier}")
        return self.hooks[verb](self.runs[int(identifier)])


def acting(runs, event=None, workflows=("check.yml",), **hooks):
    return Fake(runs, **hooks), event or body_edit("", LINE), list(workflows)


ACTING = {
    "no run yet": (acting([]), [], 0, "no run"),
    "a run of another pull request on the same head": (acting([run(number=8)]), [], 0, "no run"),
    "a completed run": (acting([run()]), ["rerun 1"], 0, "re-ran run 1"),
    "a run queued": (acting([run(status="queued")]), ["cancel 1", "rerun 1"], 0, "re-ran"),
    "a run in progress": (acting([run(status="in_progress")]), ["cancel 1", "rerun 1"], 0, "is in_progress"),
    "a run pending behind a concurrency group": (acting([run(status="pending")]), ["cancel 1", "rerun 1"], 0, "re-ran"),
    "a run waiting": (acting([run(status="waiting")]), ["cancel 1", "rerun 1"], 0, "re-ran"),
    "a run requested": (acting([run(status="requested")]), ["cancel 1", "rerun 1"], 0, "re-ran"),
    "a run awaiting approval": (acting([run(status="action_required")]), [], 0, "approval"),
    "a cancel answered 409 by a run that had finished": (
        acting([run(status="in_progress")], cancel=finish(409)),
        ["cancel 1", "rerun 1"],
        0,
        "re-ran",
    ),
    "a re-run another edit made first": (
        acting([run()], rerun=refuse_once_after_another_edit()),
        ["rerun 1", "cancel 1", "rerun 1"],
        0,
        "another edit",
    ),
    "a re-run refused at the limit": (acting([run(attempt=50)], rerun=ignore(403)), ["rerun 1"], 1, "push a commit"),
    "a re-run refused for no reason found": (acting([run()], rerun=ignore(403)), ["rerun 1"], 1, "gh run rerun 1"),
    "a run that ignores cancel and force-cancel": (
        acting([run(status="in_progress")], cancel=ignore(202), force=ignore(202)),
        ["cancel 1", "force-cancel 1"],
        1,
        "force-cancel",
    ),
    "a run that stops only on force-cancel": (
        acting([run(status="in_progress")], cancel=ignore(202)),
        ["cancel 1", "force-cancel 1", "rerun 1"],
        0,
        "re-ran",
    ),
    "a head that moved before": (acting([run()], heads=("h2",)), [], 0, "moved on"),
    "a head that moved during": (
        acting([run(), run(2, head="h2", conclusion="cancelled")], heads=("h1", "h2")),
        ["rerun 1", "cancel 1", "rerun 2"],
        0,
        "cancelled",
    ),
    "a head that moved after the re-run, whose newer run is still going": (
        acting([run(), run(2, head="h2", status="in_progress")], heads=("h1", "h2")),
        ["rerun 1", "cancel 1"],
        0,
        "is left alone",
    ),
    "a head that moved while the stale run was stopping": (
        acting([run(status="in_progress"), run(2, head="h2", status="in_progress")], heads=("h1", "h2")),
        ["cancel 1"],
        0,
        "while run 1 was stopping, so nothing was re-run",
    ),
    "a read the API refused": (
        acting([run()], forbid="/actions/runs/1"),
        [],
        1,
        "::error::GET repos/o/r/actions/runs/1 answered 403: run `gh run list -R o/r --workflow check.yml --commit h1`,"
        " then `gh run rerun <id> -R o/r`",
    ),
    "a fork, whose token cannot re-run": (
        acting(
            [run(pull_requests=[], head_repository={"full_name": "x/r"})],
            event=body_edit("", LINE, head_repository="x/r"),
        ),
        [],
        0,
        "::warning::check.yml: this pull request is from a fork",
    ),
    "a retarget": (
        acting([run()], event=edit("x", base={"ref": {"from": "main"}})),
        ["rerun 1"],
        0,
        "gh pr update-branch",
    ),
    "a file name that is no workflow": (
        acting([run()], workflows=("../x",)),
        [],
        1,
        "::error::../x is not the file name",
    ),
}


def acted_as_listed(case, calls, exit_code, said, capsys):
    api, event, workflows = case

    assert rerun_when_edited(event, workflows, "o/r", api, sleep=lambda seconds: None) == exit_code

    assert api.calls == calls
    assert said in capsys.readouterr().out


def rows(*names):
    return {name: ACTING[name] for name in names}


NO_RUN = rows("no run yet", "a run of another pull request on the same head")
LATEST_RUN = rows(
    "a completed run",
    "a run queued",
    "a run in progress",
    "a run pending behind a concurrency group",
    "a run waiting",
    "a run requested",
    "a run awaiting approval",
    "a retarget",
)
NOT_OBEYED = rows(
    "a cancel answered 409 by a run that had finished",
    "a re-run another edit made first",
    "a re-run refused at the limit",
    "a re-run refused for no reason found",
    "a run that ignores cancel and force-cancel",
    "a run that stops only on force-cancel",
)
HEAD_MOVES = rows(
    "a head that moved before",
    "a head that moved during",
    "a head that moved after the re-run, whose newer run is still going",
    "a head that moved while the stale run was stopping",
)
CANNOT_RERUN = rows("a read the API refused", "a fork, whose token cannot re-run", "a file name that is no workflow")
assert len({*NO_RUN, *LATEST_RUN, *NOT_OBEYED, *HEAD_MOVES, *CANNOT_RERUN}) == len(ACTING)


class TestReRunningACheckWhenADescriptionIsEdited:
    """Re-running a check when a description is edited · .github/actions/rerun-when-edited

    Editing a description starts no run of the check, so this action re-runs the latest one when the edit changed a
    `Depends-On:` line or the base, and only then.
    """

    class TestGivenAnEditToAPullRequest:
        @pytest.mark.parametrize(("event", "expected"), DECISIONS.values(), ids=DECISIONS)
        def test_reruns_only_when_it_changed_what_a_run_reads(self, event, expected):
            assert decide(event) == expected

    class TestGivenNoRunOfTheWorkflowForThePullRequestOnItsHead:
        """given no run of the workflow for the pull request on its head"""

        @pytest.mark.parametrize(("case", "calls", "exit_code", "said"), NO_RUN.values(), ids=NO_RUN)
        def test_calls_nothing_and_says_there_is_no_run(self, case, calls, exit_code, said, capsys):
            """calls nothing, exits 0 and says there is no run"""
            acted_as_listed(case, calls, exit_code, said, capsys)

    class TestGivenTheLatestRunOfAWorkflowOnThePullRequestsHead:
        """given the latest run of a workflow on the pull request's head"""

        @pytest.mark.parametrize(("case", "calls", "exit_code", "said"), LATEST_RUN.values(), ids=LATEST_RUN)
        def test_cancels_a_run_that_has_not_finished_and_re_runs_it_unless_it_awaits_approval(
            self, case, calls, exit_code, said, capsys
        ):
            """cancels a run that has not finished, re-runs it unless it awaits approval, and says what it did"""
            acted_as_listed(case, calls, exit_code, said, capsys)

    class TestGivenARunThatIsNotStoppedOrRestartedWhenAsked:
        """given a run that is not stopped or restarted when asked"""

        @pytest.mark.parametrize(("case", "calls", "exit_code", "said"), NOT_OBEYED.values(), ids=NOT_OBEYED)
        def test_makes_the_calls_listed_for_the_refusal_and_exits_as_listed(self, case, calls, exit_code, said, capsys):
            """makes the calls listed for the refusal, exits as listed for it and says what to do"""
            acted_as_listed(case, calls, exit_code, said, capsys)

    class TestGivenTheHeadMovesWhileTheActionWorks:
        """given the pull request's head moves while the action works"""

        @pytest.mark.parametrize(("case", "calls", "exit_code", "said"), HEAD_MOVES.values(), ids=HEAD_MOVES)
        def test_makes_the_calls_listed_for_when_it_moved_and_says_what_it_left(
            self, case, calls, exit_code, said, capsys
        ):
            """makes the calls listed for when the head moved, exits 0 and says what it left alone"""
            acted_as_listed(case, calls, exit_code, said, capsys)

    class TestGivenARequestTheActionCannotAnswerWithARerun:
        """given a read the API refuses, a pull request from a fork, or a file name that is no workflow"""

        @pytest.mark.parametrize(("case", "calls", "exit_code", "said"), CANNOT_RERUN.values(), ids=CANNOT_RERUN)
        def test_re_runs_nothing_and_says_what_to_do_instead(self, case, calls, exit_code, said, capsys):
            """re-runs nothing, exits as listed for the case and says what to do instead"""
            acted_as_listed(case, calls, exit_code, said, capsys)

    class TestGivenADescriptionOfBlankLines:
        def test_is_read_in_under_a_second_at_65536_blank_lines(self):
            newlines = "\n" * 65536
            spaces = " " * 65536
            started = time.perf_counter()

            assert decide(body_edit(newlines, newlines + LINE)) == LINES
            assert decide(body_edit(spaces + "\n", f"{spaces}x\n{LINE}")) == LINES

            assert time.perf_counter() - started < 1
