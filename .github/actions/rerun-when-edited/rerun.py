import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

from edited import base_changed, decide

LIMIT = 50
ROUNDS = 3
POLL = 5
WAIT = 120
WAIT_AFTER_FORCE = 30
WORKFLOW = re.compile(r"[\w.-]+\.ya?ml")


class Failure(Exception):
    pass


class GitHub:
    def __init__(self, token, url):
        self.token = token
        self.url = url.rstrip("/")

    def request(self, method, path):
        request = urllib.request.Request(
            f"{self.url}/{path}",
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "User-Agent": "cascade-rerun-when-edited",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as answer:
                body = answer.read().decode("utf-8")
                return answer.status, json.loads(body) if body else {}
        except urllib.error.HTTPError as error:
            return error.code, {}
        except OSError:
            return 0, {}

    def get(self, path):
        status, body = self.request("GET", path)
        if status != 200:
            raise Failure(f"GET {path} answered {status or 'nothing'}")
        return body

    def post(self, path):
        return self.request("POST", path)[0]


class Rerunner:
    def __init__(self, api, repository, pull_request, sleep=time.sleep):
        self.api = api
        self.repository = repository
        self.number = pull_request["number"]
        self.head_repository = (pull_request["head"].get("repo") or {}).get("full_name")
        self.fork = self.head_repository != repository
        self.sleep = sleep

    @property
    def runs(self):
        return f"repos/{self.repository}/actions/runs"

    def head(self):
        return self.api.get(f"repos/{self.repository}/pulls/{self.number}")["head"]["sha"]

    def is_ours(self, run):
        numbers = [pull["number"] for pull in run.get("pull_requests") or []]
        if numbers:
            return self.number in numbers
        return (run.get("head_repository") or {}).get("full_name") == self.head_repository

    def latest(self, workflow, head):
        found = self.api.get(
            f"repos/{self.repository}/actions/workflows/{workflow}/runs?head_sha={head}&event=pull_request&per_page=100"
        )["workflow_runs"]
        return max((run for run in found if self.is_ours(run)), key=lambda run: run["run_number"], default=None)

    def run(self, identifier):
        return self.api.get(f"{self.runs}/{identifier}")

    def wait(self, identifier, seconds):
        for _ in range(seconds // POLL):
            if self.run(identifier)["status"] == "completed":
                return True
            self.sleep(POLL)
        return self.run(identifier)["status"] == "completed"

    def stop(self, identifier):
        self.api.post(f"{self.runs}/{identifier}/cancel")
        if self.wait(identifier, WAIT):
            return
        print(f"run {identifier} still runs after {WAIT} s: force-cancel")
        self.api.post(f"{self.runs}/{identifier}/force-cancel")
        if self.wait(identifier, WAIT_AFTER_FORCE):
            return
        raise Failure(
            f"run {identifier} did not stop: run `gh api -X POST {self.runs}/{identifier}/force-cancel`,"
            f" then `gh run rerun {identifier} -R {self.repository}`"
        )

    def rerun(self, identifier):
        for _ in range(ROUNDS):
            before = self.run(identifier)
            if before["status"] != "completed":
                self.stop(identifier)
                before = self.run(identifier)
            if 200 <= self.api.post(f"{self.runs}/{identifier}/rerun") < 300:
                return
            after = self.run(identifier)
            if after["run_attempt"] >= LIMIT:
                raise Failure(
                    f"run {identifier} is at attempt {after['run_attempt']}, near the {LIMIT} GitHub allows,"
                    " so it will not be re-run again: push a commit"
                )
            if after["run_attempt"] <= before["run_attempt"]:
                raise Failure(
                    f"GitHub refused to re-run {identifier}: run `gh run rerun {identifier} -R {self.repository}`"
                )
            print(f"run {identifier} was re-run by another edit meanwhile: again, so that the last edit is read")
        raise Failure(
            f"run {identifier} was re-run by other edits {ROUNDS} times over:"
            f" run `gh run rerun {identifier} -R {self.repository}` once they have stopped"
        )

    def workflow(self, file, head, reasons, depth=0):
        if not WORKFLOW.fullmatch(file):
            raise Failure(f"{file} is not the file name of a workflow, such as check.yml")
        if self.head() != head:
            print(f"{file}: the head has moved on from {head[:7]}, and the newer head's own run reads the description")
            return
        run = self.latest(file, head)
        if run is None:
            print(f"{file}: no run on {head[:7]} yet, and the run that starts reads the description then")
            return
        identifier = run["id"]
        if run["status"] == "action_required":
            print(
                f"{file}: run {identifier} waits for approval, so nothing was re-run; it reads the description once approved"
            )
            return
        if self.fork:
            by_hand = "gh run rerun" if run["status"] == "completed" else "gh run cancel, wait, then gh run rerun"
            raise Failure(
                f"{file}: this pull request is from a fork, whose token cannot re-run anything, and {reasons}:"
                f" run `{by_hand} {identifier} -R {self.repository}`"
            )
        self.rerun(identifier)
        print(f"{file}: re-ran run {identifier} on {head[:7]}")
        moved = self.head()
        if moved == head:
            return
        self.api.post(f"{self.runs}/{identifier}/cancel")
        print(f"{file}: the head moved to {moved[:7]} meanwhile, so that attempt was cancelled")
        if depth < ROUNDS:
            self.workflow(file, moved, reasons, depth + 1)


def rerun_when_edited(event, workflows, repository, api, sleep=time.sleep):
    reasons = decide(event)
    if not reasons:
        print("nothing to re-run: this is not an edit that changed the Depends-On: lines or the base")
        return 0
    if not workflows:
        print("::error::no workflow is named to re-run")
        return 1
    reasons = " and ".join(reasons)
    print(f"{reasons}: re-running {', '.join(workflows)}")
    pull_request = event["pull_request"]
    rerunner = Rerunner(api, repository, pull_request, sleep)
    failed = False
    for file in workflows:
        try:
            rerunner.workflow(file, pull_request["head"]["sha"], reasons)
        except Failure as failure:
            print(f"::{'warning' if rerunner.fork else 'error'}::{failure}")
            failed = failed or not rerunner.fork
    if base_changed(event):
        print(
            "::warning::a re-run keeps the run's commit, so the pull request is still tested merged into its old base:"
            " push, or run `gh pr update-branch`, for a fresh merge"
        )
    return 1 if failed else 0


def main():
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as handle:
        event = json.load(handle)
    api = GitHub(os.environ["GITHUB_TOKEN"], os.environ.get("GITHUB_API_URL") or "https://api.github.com")
    return rerun_when_edited(event, os.environ.get("WORKFLOWS", "").split(), os.environ["GITHUB_REPOSITORY"], api)


if __name__ == "__main__":
    sys.exit(main())
