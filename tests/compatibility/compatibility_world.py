import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "scripts" / "compatibility.py"
SYNTHETIC_ADAPTER = ROOT / "fixtures" / "synthetic-adapter"
FAKE_ENGINE = ROOT / "fixtures" / "fake-engine"
CONTEXT_IRI = "https://ns.cascadeprotocol.org/bridge/v1-draft/compatibility.jsonld"

IDENTITY = [
    "-c", "user.name=compatibility tests",
    "-c", "user.email=tests@example.org",
    "-c", "commit.gpgsign=false",
    "-c", "tag.gpgsign=false",
]


def git(*args, cwd=None):
    run = subprocess.run(
        ["git", *IDENTITY, *args], cwd=cwd, capture_output=True, encoding="utf-8"
    )
    assert run.returncode == 0, f"git {' '.join(args)}: {run.stderr.strip()}"
    return run.stdout.strip()


def publish(origins, name, fill):
    path = origins / name
    path.mkdir()
    fill(path)
    git("init", "-q", "-b", "main", str(path))
    git("add", "-A", cwd=path)
    git("commit", "-q", "-m", f"{name}: first", cwd=path)
    return git("rev-parse", "HEAD", cwd=path)


def publish_origins(origins):
    origins.mkdir(parents=True)
    commits = {}
    commits["specification"] = publish(
        origins, "specification",
        lambda path: (path / "README.md").write_text("a stand-in for the specification\n", encoding="utf-8"),
    )
    commits["adapter"] = publish(
        origins, "adapter", lambda path: shutil.copytree(SYNTHETIC_ADAPTER, path, dirs_exist_ok=True)
    )
    adapter = origins / "adapter"
    git("tag", "-a", "v1", "-m", "v1", cwd=adapter)
    git("checkout", "-q", "-b", "feat/next", cwd=adapter)
    (adapter / "NOTICE").write_text("next\n", encoding="utf-8")
    git("add", "-A", cwd=adapter)
    git("commit", "-q", "-m", "feat: next", cwd=adapter)
    commits["adapter feat/next"] = git("rev-parse", "HEAD", cwd=adapter)
    git("checkout", "-q", "main", cwd=adapter)

    def engine(path):
        shutil.copytree(FAKE_ENGINE, path, dirs_exist_ok=True)
        specification = {"codeRepository": (origins / "specification").as_uri(), "commit": commits["specification"]}
        write_compatibility(path, engine_document(specification, []))

    commits["engine"] = publish(origins, "engine", engine)
    return commits


def write_compatibility(directory, document):
    body = {"@context": CONTEXT_IRI, **document}
    (directory / "compatibility.json").write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8", newline="")


def read_compatibility(directory):
    document = json.loads((directory / "compatibility.json").read_text(encoding="utf-8"))
    document.pop("@context")
    return document


def engine_document(spec_pin, must_pass_with, canned="passed", **overrides):
    document = {
        "specPin": spec_pin,
        "setup": [sys.executable, "-c", "pass"],
        "command": [sys.executable, "engine.py", "--canned", canned],
        "mustPassWith": must_pass_with,
    }
    document.update(overrides)
    return {key: value for key, value in document.items() if value is not None}


class World:
    def __init__(self, root, origins, commits):
        self.root = root
        self.origins = origins
        self.commits = dict(commits)
        self.workspace = root / "workspace"
        self.temporary = root / "tmp"
        self.workspace.mkdir()
        self.temporary.mkdir()

    def own_origins(self):
        copy = self.root / "origins"
        shutil.copytree(self.origins, copy)
        self.origins = copy
        return self

    def url(self, name):
        return (self.origins / name).as_uri()

    def clone(self, name):
        path = self.workspace / name
        git("clone", "-q", self.url(name), str(path))
        return path

    def spec_pin(self):
        return {"codeRepository": self.url("specification"), "commit": self.commits["specification"]}

    def engine_file(self, must_pass_with, canned="passed", **overrides):
        return engine_document(self.spec_pin(), must_pass_with, canned, **overrides)

    def adapter_pin(self, **pin):
        return [{"codeRepository": self.url("adapter"), **pin}]

    def engine(self, must_pass_with, canned="passed", **overrides):
        engine = self.clone("engine")
        write_compatibility(engine, self.engine_file(must_pass_with, canned, **overrides))
        return engine

    @property
    def environment(self):
        temporary = str(self.temporary)
        environment = dict(os.environ, TMPDIR=temporary, TEMP=temporary, TMP=temporary, PYTHONIOENCODING="utf-8")
        environment.pop("CI", None)
        return environment

    def tool(self, subject, *steps, mode="local", interpreter=(sys.executable,)):
        output = ""
        for command, expected in steps:
            run = subprocess.run(
                [*interpreter, str(TOOL), command, str(subject), "--mode", mode],
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                env=self.environment,
            )
            output += run.stdout + run.stderr
            assert run.returncode == expected, f"{command} exited {run.returncode}, {expected} expected\n{output}"
        return output

    def record(self, subject):
        path = self.temporary / "cascade-compatibility" / subject.name / "record.json"
        return json.loads(path.read_text(encoding="utf-8"))


def sibling_state(path):
    return (
        git("rev-parse", "HEAD", cwd=path),
        git("symbolic-ref", "--short", "HEAD", cwd=path),
        git("status", "--porcelain", cwd=path),
    )
