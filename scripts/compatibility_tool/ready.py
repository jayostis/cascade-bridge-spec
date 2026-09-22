import os

from compatibility_tool.console import Status, report
from compatibility_tool.github import named_in


def names_back(api, entry, under_test):
    reached = {entry}
    walking = [entry]
    while walking:
        pull = api.pull_request(walking.pop(0), refuse=False)
        for named in named_in((pull or {}).get("body")):
            if named == under_test:
                return True
            if named not in reached:
                reached.add(named)
                walking.append(named)
    return False


def not_succeeded(api, entry, pull):
    own_gate = os.environ.get("GITHUB_JOB")
    return [
        run
        for run in api.check_runs(entry.path, pull.get("head", {}).get("sha"))
        if run.get("name") != own_gate and (run.get("status"), run.get("conclusion")) != ("completed", "success")
    ]


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
    failed = 0
    for entry in named:
        pull = api.pull_request(entry)
        if pull.get("merged"):
            report(True, f"{entry.label} has merged")
        elif pull.get("state") != "open":
            failed += 1
            report(False, f"{entry.label} is closed without merging: cut the Depends-On: line naming it")
        elif not names_back(api, entry, under_test):
            failed += 1
            report(False, f"{entry.label} has not merged, and this pull request merges only after it does")
        else:
            waiting = not_succeeded(api, entry, pull)
            for run in waiting:
                report(
                    False,
                    f"{entry.label} names this pull request back, and its {run.get('name')} has not "
                    f"succeeded: {run.get('conclusion') or run.get('status')}",
                )
            if waiting:
                failed += 1
            else:
                report(True, f"{entry.label} names this pull request back, and its checks have succeeded")
    return Status.FAIL if failed else Status.OK
