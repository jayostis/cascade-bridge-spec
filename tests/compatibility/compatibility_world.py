import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "scripts" / "compatibility.py"
SYNTHETIC_ADAPTER = ROOT / "fixtures" / "synthetic-adapter"
FAKE_ENGINE = ROOT / "fixtures" / "fake-engine"
CONTEXT_IRI = "https://ns.cascadeprotocol.org/bridge/v1-draft/compatibility.jsonld"
OWNER = "jayostis"
CRATE = "ro-crate-metadata.json"

VOCABULARY = "spec"
VOCABULARY_OWNER = "the-cascade-protocol"
VOCABULARY_PATH = f"{VOCABULARY_OWNER}/{VOCABULARY}"
VOCABULARY_URL = f"https://github.com/{VOCABULARY_PATH}"
VOCABULARY_NAMESPACE = "https://example.org/synthetic-adapter/v1#"
AN_ONTOLOGY = "ontologies/example/v1/example.ttl"
ITS_SHAPES = "ontologies/example/v1/example.shapes.ttl"
VOCABULARY_FILES = (AN_ONTOLOGY, ITS_SHAPES)
CRATES_NAMING_THE_VOCABULARY = (("adapter", "."), ("cascade-bridge-spec", "fixtures/synthetic-adapter"))

THE_ONTOLOGY = """@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix ex:  <https://example.org/synthetic-adapter/v1#> .

<https://example.org/synthetic-adapter/v1#> a owl:Ontology .

ex:Record a owl:Class .

ex:status a owl:ObjectProperty .
"""

THE_SHAPES = """@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix sh:  <http://www.w3.org/ns/shacl#> .

<> a owl:Ontology .

<#Record> a sh:NodeShape ;
  sh:targetClass <https://example.org/synthetic-adapter/v1#Record> .
"""

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


def publish(origins, name, fill, owner=OWNER):
    path = origins / owner / name
    path.mkdir(parents=True)
    fill(path)
    git("init", "-q", "-b", "main", str(path))
    git("add", "-A", cwd=path)
    git("commit", "-q", "-m", f"{name}: first", cwd=path)
    git("config", "uploadpack.allowAnySHA1InWant", "true", cwd=path)
    return git("rev-parse", "HEAD", cwd=path)


def specification(path):
    """What a run fetches and runs the checks from: this working tree, uncommitted edits included."""
    for directory in ("scripts", "vocab", "shapes", "adapter", "engine", "fixtures"):
        shutil.copytree(ROOT / directory, path / directory, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(ROOT / "pyproject.toml", path / "pyproject.toml")


def vocabulary(path):
    """the-cascade-protocol/spec as this world serves it: the ontologies and shapes an adapter names files of."""
    for relative, body in ((AN_ONTOLOGY, THE_ONTOLOGY), (ITS_SHAPES, THE_SHAPES)):
        written = path / relative
        written.parent.mkdir(parents=True, exist_ok=True)
        written.write_text(body, encoding="utf-8", newline="")


def name_vocabulary(crate_file, url, commit, files=VOCABULARY_FILES):
    """An adapter's crate, naming the-cascade-protocol/spec at a commit and the files it reads there."""
    document = json.loads(crate_file.read_text(encoding="utf-8"))
    document["@context"][1]["bridge:vocabularyFile"] = "bridge:vocabularyFile"
    root = next(entity for entity in document["@graph"] if entity["@id"] == "./")
    named = f"{url}/commit/{commit}"
    was = root["bridge:cascadeVocabularyPin"]["@id"]
    root["bridge:cascadeVocabularyPin"] = {"@id": named}
    root["bridge:vocabularyFile"] = list(files)
    root["hasPart"] = [{"@id": named} if part == {"@id": was} else part for part in root["hasPart"]]
    for entity in document["@graph"]:
        if entity["@id"] == was:
            entity["@id"] = named
            entity["codeRepository"] = {"@id": url}
            entity["version"] = commit
    crate_file.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="")


def publish_origins(origins):
    origins.mkdir(parents=True)
    commits = {}
    commits["cascade-bridge-spec"] = publish(origins, "cascade-bridge-spec", specification)
    commits[VOCABULARY] = publish(origins, VOCABULARY, vocabulary, owner=VOCABULARY_OWNER)
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


def a_host(name="native", canned="passed", **overrides):
    host = {
        "name": name,
        "setup": [sys.executable, "-c", "pass"],
        "command": [sys.executable, "engine.py", "--canned", canned],
    }
    host.update(overrides)
    return {key: value for key, value in host.items() if value is not None}


def engine_document(must_pass_with, canned="passed", host=(), **overrides):
    """One host, native, unless hosts are given; a setup or command override is that one host's."""
    if host == ():
        in_the_host = {key: overrides.pop(key) for key in ("setup", "command") if key in overrides}
        host = [a_host(canned=canned, **in_the_host)]
    document = {"host": host, "mustPassWith": must_pass_with}
    document.update(overrides)
    return {key: value for key, value in document.items() if value is not None}


class PullRequests:
    """The fields the tooling reads from GitHub, served from memory over HTTP."""

    def __init__(self):
        self.by_repository = {}
        self.comments = []
        self.refusals = {}
        self.check_runs_by_commit = {}

    def refuse(self, repository, number, status, headers=None):
        self.refusals[(repository, number)] = (status, dict(headers or {}))

    def open(self, repository, number, body="", base="main", head=None, state="open", merged=False):
        pull = {
            "number": number,
            "body": body,
            "state": state,
            "merged": merged,
            "base": {"ref": base},
            "head": {"sha": head or ""},
            "merge_commit_sha": None,
        }
        self.by_repository.setdefault(repository, {})[number] = pull
        return pull

    def merged_as(self, repository, number, commit):
        """The commit the target branch holds once the pull request merged, however it was merged."""
        self.get(repository, number)["merge_commit_sha"] = commit

    def get(self, repository, number):
        return self.by_repository.get(repository, {}).get(number)

    def check_run(self, repository, commit, name, status="completed", conclusion="success"):
        run = {
            "id": sum(len(runs) for runs in self.check_runs_by_commit.values()) + 1,
            "name": name,
            "head_sha": commit,
            "status": status,
            "conclusion": conclusion if status == "completed" else None,
        }
        self.check_runs_by_commit.setdefault((repository, commit), []).append(run)
        return run["id"]

    def check_run_by_id(self, identifier):
        for runs in self.check_runs_by_commit.values():
            for run in runs:
                if run["id"] == identifier:
                    return run
        return None

    def check_runs(self, repository, commit, page, per_page):
        runs = self.check_runs_by_commit.get((repository, commit), [])
        return {"total_count": len(runs), "check_runs": runs[(page - 1) * per_page : page * per_page]}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *arguments):
        pass

    def answer(self, status, body, headers=None):
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(payload)

    def parts(self):
        return urlsplit(self.path).path.strip("/").split("/")

    def query(self, name, default):
        return int(parse_qs(urlsplit(self.path).query).get(name, [default])[0])

    def do_GET(self):
        parts = self.parts()
        if len(parts) == 6 and parts[0] == "repos" and parts[3] == "commits" and parts[5] == "check-runs":
            page, per_page = self.query("page", 1), self.query("per_page", 30)
            return self.answer(200, self.server.pull_requests.check_runs(parts[2], parts[4], page, per_page))
        if len(parts) == 5 and parts[0] == "repos" and parts[3] == "check-runs":
            run = self.server.pull_requests.check_run_by_id(int(parts[4]))
            return self.answer(200, run) if run else self.answer(404, {"message": "Not Found"})
        if len(parts) == 5 and parts[0] == "repos" and parts[3] == "pulls":
            refusal = self.server.pull_requests.refusals.get((parts[2], int(parts[4])))
            if refusal:
                status, headers = refusal
                return self.answer(status, {"message": "refused"}, headers)
            pull = self.server.pull_requests.get(parts[2], int(parts[4]))
            return self.answer(200 if pull else 404, pull or {"message": "Not Found"})
        return self.answer(404, {"message": "Not Found"})

    def do_POST(self):
        parts = self.parts()
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8")
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
        return self.pin_vocabularies()

    def pin_vocabularies(self, commit=None, files=VOCABULARY_FILES):
        """Every adapter crate in these origins names this world's the-cascade-protocol/spec at a commit of it."""
        for name, relative in CRATES_NAMING_THE_VOCABULARY:
            origin = self.origin(name)
            name_vocabulary(origin / relative / CRATE, VOCABULARY_URL, commit or self.commits[VOCABULARY], files)
            git("add", "-A", cwd=origin)
            git("commit", "-q", "--allow-empty", "-m", "the vocabulary this adapter reads", cwd=origin)
        return self

    def url(self, name):
        return self.origin(name).as_uri()

    def origin(self, name):
        return self.origins / (VOCABULARY_OWNER if name == VOCABULARY else OWNER) / name

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
        for name in (
            "GITHUB_REPOSITORY",
            "GITHUB_EVENT_PATH",
            "GITHUB_REF_NAME",
            "GITHUB_STEP_SUMMARY",
            "GITHUB_TOKEN",
            "CASCADE_CHECK_RUN_ID",
        ):
            environment.pop(name, None)
        environment.update({key: str(value) for key, value in extra.items()})
        return environment

    def ci(self, repository="engine", event=None, branch="main", gate=None):
        """The variables a workflow run gives the tooling."""
        variables = {
            "CI": "true",
            "GITHUB_REPOSITORY": f"{OWNER}/{repository}",
            "GITHUB_API_URL": self.api_url,
            "GITHUB_TOKEN": "a token the stub does not check",
            "GITHUB_WORKSPACE": str(self.workspace),
            "GITHUB_SERVER_URL": str(self.origins.as_uri()),
            "GITHUB_STEP_SUMMARY": str(self.summary),
            "GITHUB_REF_NAME": branch,
        }
        if event is not None:
            variables["GITHUB_EVENT_PATH"] = str(event)
        if gate is not None:
            own = self.pull_requests.check_run(repository, "the gate's own commit", gate, status="in_progress")
            variables["CASCADE_CHECK_RUN_ID"] = own
        return variables

    def tool(self, subject, expected=0, check=None, interpreter=(sys.executable,), arguments=(), **variables):
        argv = [*interpreter, str(TOOL), str(subject), "--results", str(self.results), *arguments]
        if check:
            argv += ["--check", check]
        if variables.get("CI") == "true":  # start passes it as an argument, and sets no variable
            argv += ["--spec-repository", self.url("cascade-bridge-spec")]
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

    def table_in_results(self):
        written = self.results / "table.md"
        return written.read_text(encoding="utf-8") if written.exists() else ""


def current_branch(path):
    return git("symbolic-ref", "--short", "HEAD", cwd=path)
