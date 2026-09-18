from compatibility_tool.console import Status, report
from compatibility_tool.github import named_in


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
        elif pull.get("state") == "open":
            failed += 1
            report(False, f"{entry.label} has not merged, and this pull request merges only after it does")
        else:
            failed += 1
            report(False, f"{entry.label} is closed without merging: cut the Depends-On: line naming it")
    return Status.FAIL if failed else Status.OK
