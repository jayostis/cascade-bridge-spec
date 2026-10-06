import os
from time import monotonic, sleep

from compatibility_tool.console import Status, Stop, report
from compatibility_tool.github import named_in

PASSING = ("success", "skipped", "neutral")
WAIT = 45 * 60
POLL = 30


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


def latest(runs):
    """A check's latest run on the commit: a rerun replaces the run it reran, and has the larger id."""
    by_name = {}
    for run in sorted(runs, key=lambda run: run.get("id") or 0):
        by_name[run.get("name")] = run
    return list(by_name.values())


def failed(run):
    return run.get("status") == "completed" and run.get("conclusion") not in PASSING


def check(directory, options, event, api):
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
    failures = 0
    for entry in named:
        pull = api.pull_request(entry)
        if pull.get("merged"):
            report(True, f"{entry.label} has merged")
        elif pull.get("state") != "open":
            failures += 1
            report(False, f"{entry.label} is closed without merging: cut the Depends-On: line naming it")
        elif entry not in members:
            failures += 1
            report(False, f"{entry.label} has not merged, and this pull request merges only after it does")
    gate = own_gate(api, event) if members else None
    for member in members:
        for outside in naming[member]:
            if outside == under_test or outside in members or api.pull_request(outside).get("merged"):
                continue
            failures += 1
            report(
                False,
                f"{member.label} names this pull request back, and names {outside.label}, which has not merged "
                "and does not: a cycle merges only once everything it names outside itself has",
            )
    return Status.FAIL if failures + members_checks(api, members, gate, failures) else Status.OK


def members_checks(api, members, gate, failures):
    """How many members failed, waiting while a member's checks have not finished and none has failed."""
    deadline = monotonic() + WAIT
    waiting = list(members)
    while True:
        unfinished = {}
        for member in waiting:
            head = api.pull_request(member).get("head", {}).get("sha")
            runs = latest([run for run in api.check_runs(member.path, head) if run.get("name") != gate])
            broken = [run for run in runs if failed(run)]
            for run in broken:
                report(
                    False,
                    f"{member.label} names this pull request back, and its {run.get('name')} has not "
                    f"succeeded: {run.get('conclusion')}",
                )
            if broken:
                failures += 1
            elif runs and all(run.get("status") == "completed" for run in runs):
                report(True, f"{member.label} names this pull request back, and its checks have succeeded")
            else:
                unfinished[member] = [run for run in runs if run.get("status") != "completed"]
        if not unfinished:
            return failures
        if failures or monotonic() >= deadline:
            waited = f"after waiting {WAIT // 60} minutes" if not failures else "and the gate has already failed"
            for member, runs in unfinished.items():
                said = (
                    ", ".join(f"{run.get('name')} is {run.get('status')}" for run in runs)
                    or "it has no checks on its head commit"
                )
                report(
                    False,
                    f"{member.label} names this pull request back, and its checks have not finished {waited}: {said}",
                )
            return failures + len(unfinished)
        names = ", ".join(member.label for member in unfinished)
        print(f"  waiting {POLL} seconds for the checks of {names} to finish")
        sleep(POLL)
        waiting = list(unfinished)
