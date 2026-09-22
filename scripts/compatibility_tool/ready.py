import os

from compatibility_tool.console import Status, Stop, report
from compatibility_tool.github import named_in

PASSING = ("success", "skipped", "neutral")


def is_open(pull):
    return bool(pull) and pull.get("state") == "open" and not pull.get("merged")


def open_pull_requests_reached(api, under_test):
    naming = {}
    walking = [under_test]
    while walking:
        entry = walking.pop(0)
        pull = api.pull_request(entry, refuse=False)
        if entry != under_test and not is_open(pull):
            continue
        naming[entry] = named_in((pull or {}).get("body"))
        walking += [named for named in naming[entry] if named not in naming and named not in walking]
    return naming


def cycle(naming, under_test):
    members = {under_test}
    grew = True
    while grew:
        joining = [entry for entry, named in naming.items() if entry not in members and members.intersection(named)]
        members.update(joining)
        grew = bool(joining)
    return [entry for entry in naming if entry in members and entry != under_test]


def own_gate(api, event):
    identifier = os.environ.get("CASCADE_CHECK_RUN_ID")
    if not identifier:
        raise Stop(
            "this pull request is in a cycle, and the merge gate tells its own check on the others only from "
            "CASCADE_CHECK_RUN_ID, which the start action sets"
        )
    return api.check_run(event.repository, identifier).get("name")


def not_succeeded(runs):
    return [run for run in runs if run.get("status") != "completed" or run.get("conclusion") not in PASSING]


def check(event, api):
    print("Every pull request this one names, at merge time")
    under_test = event.under_test
    if under_test is None:
        report(True, "no pull request is under test")
        return Status.OK
    named = named_in(api.pull_request(under_test).get("body"))
    if not named:
        report(True, f"{under_test.label} names no pull request")
        return Status.OK
    naming = open_pull_requests_reached(api, under_test)
    members = cycle(naming, under_test)
    failed = 0
    for entry in named:
        pull = api.pull_request(entry)
        if pull.get("merged"):
            report(True, f"{entry.label} has merged")
        elif pull.get("state") != "open":
            failed += 1
            report(False, f"{entry.label} is closed without merging: cut the Depends-On: line naming it")
        elif entry not in members:
            failed += 1
            report(False, f"{entry.label} has not merged, and this pull request merges only after it does")
    gate = own_gate(api, event) if members else None
    for member in members:
        for outside in naming[member]:
            if outside == under_test or outside in members or api.pull_request(outside).get("merged"):
                continue
            failed += 1
            report(
                False,
                f"{member.label} names this pull request back, and names {outside.label}, which has not merged "
                "and does not: a cycle merges only once everything it names outside itself has",
            )
        pull = api.pull_request(member)
        runs = [run for run in api.check_runs(member.path, pull.get("head", {}).get("sha")) if run.get("name") != gate]
        if not runs:
            failed += 1
            report(False, f"{member.label} names this pull request back, and has no checks on its head commit yet")
            continue
        waiting = not_succeeded(runs)
        for run in waiting:
            report(
                False,
                f"{member.label} names this pull request back, and its {run.get('name')} has not "
                f"succeeded: {run.get('conclusion') or run.get('status')}",
            )
        if waiting:
            failed += 1
        else:
            report(True, f"{member.label} names this pull request back, and its checks have succeeded")
    return Status.FAIL if failed else Status.OK
