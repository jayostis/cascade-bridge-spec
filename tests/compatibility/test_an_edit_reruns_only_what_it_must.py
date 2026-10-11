import pytest

from edited import decide
from rerun import rerun_when_edited

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


@pytest.mark.parametrize(("event", "expected"), DECISIONS.values(), ids=DECISIONS)
def test_an_edit_reruns_only_when_it_changed_what_a_run_reads(event, expected):
    assert decide(event) == expected


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
    def __init__(self, runs, heads=("h1",), cancel=None, force=None, rerun=None):
        self.runs = {found["id"]: found for found in runs}
        self.heads = list(heads)
        self.calls = []
        self.hooks = {
            "cancel": cancel or finish(202),
            "force-cancel": force or finish(202),
            "rerun": rerun or restart(201),
        }

    def get(self, path):
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
        acting([run(), run(2, head="h2")], heads=("h1", "h2")),
        ["rerun 1", "cancel 1", "rerun 2"],
        0,
        "cancelled",
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


@pytest.mark.parametrize(("case", "calls", "exit_code", "said"), ACTING.values(), ids=ACTING)
def test_a_stale_run_is_stopped_if_it_runs_and_run_again_and_a_refusal_says_what_to_do_by_hand(
    case, calls, exit_code, said, capsys
):
    api, event, workflows = case

    assert rerun_when_edited(event, workflows, "o/r", api, sleep=lambda seconds: None) == exit_code

    assert api.calls == calls
    assert said in capsys.readouterr().out
