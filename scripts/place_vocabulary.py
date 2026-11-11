#!/usr/bin/env python3
"""Usage:

    python3 scripts/place_vocabulary.py <destination>

Places cascade-vocabulary at <destination>, in a job that reads it as a sibling of this repository: the head of the
pull request under test's `Depends-On:` line for it, else its default branch.
"""

import subprocess
import sys

from compatibility_tool import github
from compatibility_tool.console import Stop

VOCABULARY = "cascade-vocabulary"


def named_head(api, event):
    """The head of the vocabulary pull request the pull request under test names, as (clone url, commit), or None."""
    if event.under_test is None:
        return None
    names = [
        named
        for named in github.named_in(api.pull_request(event.under_test).get("body"))
        if github.repository_name(named.path) == VOCABULARY
    ]
    if not names:
        return None
    if len(names) > 1:
        raise Stop(f"Depends-On: names {VOCABULARY} twice, {names[0].label} and {names[1].label}; name one")
    head = api.pull_request(names[0])["head"]
    if not head.get("repo"):
        raise Stop(f"{names[0].label} has no head repository to place {VOCABULARY} from")
    return head["repo"]["clone_url"], head["sha"]


def git(*arguments):
    subprocess.run(["git", *arguments], check=True)


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    destination = argv[1]
    github.take_token()
    api = github.Api()
    event = github.event(api)
    named = named_head(api, event)
    url, ref = named or (github.url_on_this_server(f"{event.repository.split('/')[0]}/{VOCABULARY}"), "HEAD")
    git("init", "--quiet", destination)
    git("-C", destination, "fetch", "--quiet", "--depth", "1", url, ref)
    git("-C", destination, "checkout", "--quiet", "--detach", "FETCH_HEAD")
    print(f"{VOCABULARY} at {url} {ref if named else 'default branch'}, placed at {destination}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Stop as stop:
        print(f"::error::{stop}")
        sys.exit(1)
