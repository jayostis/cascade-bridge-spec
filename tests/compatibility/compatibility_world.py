import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "scripts" / "compatibility.py"
SYNTHETIC_ADAPTER = ROOT / "fixtures" / "synthetic-adapter"
FAKE_ENGINE = ROOT / "fixtures" / "fake-engine"
CONTEXT_IRI = "https://ns.cascadeprotocol.org/bridge/v1-draft/compatibility.jsonld"
OWNER = "jayostis"

SETTINGS = (
    "user.name=compatibility tests",
    "user.email=tests@example.org",
    "commit.gpgsign=false",
    "tag.gpgsign=false",
    "core.autocrlf=false",
)
IDENTITY = [argument for setting in SETTINGS for argument in ("-c", setting)]


def git(*args, cwd=None):
    run = subprocess.run(["git", *IDENTITY, *args], cwd=cwd, capture_output=True, encoding="utf-8")
    assert run.returncode == 0, f"git {' '.join(args)}: {run.stderr.strip()}"
    return run.stdout.strip()


def publish(origins, name, fill):
    path = origins / OWNER / name
    path.mkdir(parents=True)
    fill(path)
    git("init", "-q", "-b", "main", str(path))
    git("add", "-A", cwd=path)
    git("commit", "-q", "-m", f"{name}: first", cwd=path)
    git("config", "uploadpack.allowAnySHA1InWant", "true", cwd=path)
    return git("rev-parse", "HEAD", cwd=path)


def specification(path):
    """What a run fetches and runs the checks from: this working tree, uncommitted edits included."""
    for directory in ("scripts", "vocab", "shapes", "adapter", "fixtures"):
        shutil.copytree(ROOT / directory, path / directory, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(ROOT / "pyproject.toml", path / "pyproject.toml")


def publish_origins(origins):
    origins.mkdir(parents=True)
    commits = {}
    commits["cascade-bridge-spec"] = publish(origins, "cascade-bridge-spec", specification)
    commits["adapter"] = publish(
        origins, "adapter", lambda path: shutil.copytree(SYNTHETIC_ADAPTER, path, dirs_exist_ok=True)
    )

    def engine(path):
        shutil.copytree(FAKE_ENGINE, path, dirs_exist_ok=True)
        write_compatibility(path, engine_document([]))

    commits["engine"] = publish(origins, "engine", engine)
    return commits


def write_compatibility(directory, document):
    body = {"@context": CONTEXT_IRI, **document}
    (directory / "compatibility.json").write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8", newline="")


def engine_document(must_pass_with, canned="passed", **overrides):
    document = {
        "setup": [sys.executable, "-c", "pass"],
        "command": [sys.executable, "engine.py", "--canned", canned],
        "mustPassWith": must_pass_with,
    }
    document.update(overrides)
    return {key: value for key, value in document.items() if value is not None}


class PullRequests:
    """The fields the tooling reads from GitHub, served from memory over HTTP."""

    def __init__(self):
        self.by_repository = {}
        self.comments = []
        self.refuse_comments = False

    def open(self, repository, number, body="", base="main", head=None, state="open", merged=False):
        pull = {
            "number": number,
            "body": body,
            "state": state,
            "merged": merged,
            "base": {"ref": base},
            "head": {"sha": head or ""},
        }
        self.by_repository.setdefault(repository, {})[number] = pull
        return pull

    def get(self, repository, number):
        return self.by_repository.get(repository, {}).get(number)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *arguments):
        pass

    def answer(self, status, body):
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def parts(self):
        return self.path.strip("/").split("/")

    def do_GET(self):
        parts = self.parts()
        if len(parts) == 5 and parts[0] == "repos" and parts[3] == "pulls":
            pull = self.server.pull_requests.get(parts[2], int(parts[4]))
            return self.answer(200 if pull else 404, pull or {"message": "Not Found"})
        return self.answer(404, {"message": "Not Found"})

    def do_POST(self):
        parts = self.parts()
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8")
        if self.server.pull_requests.refuse_comments:
            return self.answer(403, {"message": "Resource not accessible by integration"})
        if len(parts) == 6 and parts[3] == "issues" and parts[5] == "comments":
            self.server.pull_requests.comments.append((parts[2], int(parts[4]), json.loads(body)["body"]))
            return self.answer(201, {"id": len(self.server.pull_requests.comments)})
        return self.answer(404, {"message": "Not Found"})


class Api:
    def __init__(self, pull_requests):
        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.server.pull_requests = pull_requests
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


class World:
    def __init__(self, root, origins, commits, pull_requests, api_url):
        self.root = root
        self.origins = origins
        self.commits = dict(commits)
        self.pull_requests = pull_requests
        self.api_url = api_url
        self.workspace = root / "workspace"
        self.temporary = root / "tmp"
        self.results = root / "results"
        self.workspace.mkdir()
        self.temporary.mkdir()
        self.summary = root / "summary.md"

    def own_origins(self):
        copy = self.root / "origins"
        shutil.copytree(self.origins, copy)
        self.origins = copy
        return self

    def url(self, name):
        return (self.origins / OWNER / name).as_uri()

    def origin(self, name):
        return self.origins / OWNER / name

    def clone(self, name):
        path = self.workspace / name
        git("clone", "-q", self.url(name), str(path))
        return path

    def branch(self, name, branch, fill=None):
        """A branch on an origin, as a pull request's head or a matching branch."""
        origin = self.origin(name)
        git("checkout", "-q", "-b", branch, cwd=origin)
        if fill:
            fill(origin)
            git("add", "-A", cwd=origin)
            git("commit", "-q", "-m", f"{branch}: a change", cwd=origin)
        head = git("rev-parse", "HEAD", cwd=origin)
        git("checkout", "-q", "main", cwd=origin)
        return head

    def commit_on_main(self, name, line):
        origin = self.origin(name)
        (origin / line).write_text(f"{line}\n", encoding="utf-8")
        git("add", "-A", cwd=origin)
        git("commit", "-q", "-m", line, cwd=origin)
        return git("rev-parse", "HEAD", cwd=origin)

    def pull_request(self, name, number, body="", base="main", fill=None, state="open", merged=False):
        if not self.origin(name).exists():  # a repository this run checks nothing out from
            self.pull_requests.open(name, number, body=body, base=base, state=state, merged=merged)
            return None
        head = self.branch(name, f"pull/{number}", fill)
        git("update-ref", f"refs/pull/{number}/head", head, cwd=self.origin(name))
        self.pull_requests.open(name, number, body=body, base=base, head=head, state=state, merged=merged)
        return head

    def engine(self, must_pass_with, canned="passed", **overrides):
        engine = self.clone("engine")
        write_compatibility(engine, engine_document(must_pass_with, canned, **overrides))
        return engine

    def event(self, number, repository="engine"):
        pull = self.pull_requests.get(repository, number) or {"base": {"ref": "main"}}
        path = self.root / "event.json"
        body = {"pull_request": {"number": number, "base": {"ref": pull["base"]["ref"]}}}
        path.write_text(json.dumps(body), encoding="utf-8")
        return path

    def environment(self, **extra):
        temporary = str(self.temporary)
        environment = dict(
            os.environ,
            TMPDIR=temporary,
            TEMP=temporary,
            TMP=temporary,
            PYTHONIOENCODING="utf-8",
            # A digested fixture is bytes: a checkout that rewrote its line endings is a different file.
            GIT_CONFIG_COUNT="1",
            GIT_CONFIG_KEY_0="core.autocrlf",
            GIT_CONFIG_VALUE_0="false",
        )
        environment.pop("CI", None)
        for name in ("GITHUB_REPOSITORY", "GITHUB_EVENT_PATH", "GITHUB_REF_NAME", "GITHUB_STEP_SUMMARY"):
            environment.pop(name, None)
        environment.update({key: str(value) for key, value in extra.items()})
        return environment

    def ci(self, repository="engine", event=None, branch="main"):
        """The variables a workflow run gives the tooling."""
        variables = {
            "CI": "true",
            "GITHUB_REPOSITORY": f"{OWNER}/{repository}",
            "GITHUB_API_URL": self.api_url,
            "GITHUB_TOKEN": "a token the stub does not check",
            "GITHUB_WORKSPACE": str(self.workspace),
            "GITHUB_SERVER_URL": str(self.origins.as_uri()),
            "CASCADE_SPEC_REPOSITORY": self.url("cascade-bridge-spec"),
            "GITHUB_STEP_SUMMARY": str(self.summary),
            "GITHUB_REF_NAME": branch,
        }
        if event is not None:
            variables["GITHUB_EVENT_PATH"] = str(event)
        return variables

    def tool(self, subject, expected=0, check=None, interpreter=(sys.executable,), arguments=(), **variables):
        argv = [*interpreter, str(TOOL), str(subject), "--results", str(self.results), *arguments]
        if check:
            argv += ["--check", check]
        run = subprocess.run(
            argv, capture_output=True, encoding="utf-8", errors="replace", env=self.environment(**variables)
        )
        said = run.stdout + run.stderr
        assert run.returncode == expected, f"exited {run.returncode}, {expected} expected\n{said}"
        return said

    def record(self):
        return json.loads((self.results / "record.json").read_text(encoding="utf-8"))

    def table(self):
        return self.summary.read_text(encoding="utf-8") if self.summary.exists() else ""


def current_branch(path):
    return git("symbolic-ref", "--short", "HEAD", cwd=path)
