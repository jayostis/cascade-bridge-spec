import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from compatibility_tool.console import Stop
from compatibility_tool.document import Pin, read_json

RECORD = "record.json"


class Source(Enum):
    COMMIT = "commit"
    TAG = "tag"
    BRANCH_TIP = "branch tip"
    WORKING_TREE = "working tree"
    BRANCH_LAST_COMMIT = "branch last commit"

    @property
    def wording(self):
        return {
            Source.COMMIT: "the commit pinned",
            Source.TAG: "the tag",
            Source.BRANCH_TIP: "the branch's tip",
            Source.WORKING_TREE: "the sibling's working tree",
            Source.BRANCH_LAST_COMMIT: "the branch's last commit",
        }[self]


def optional_path(value):
    return None if value is None else Path(value)


def optional_text(value):
    return None if value is None else str(value)


@dataclass
class ResolvedPin:
    pin: Pin
    commit: str | None
    source: Source
    uncommitted_edits: bool = False
    warning: str | None = None
    path: Path | None = None
    adapter: Path | None = None
    report: Path | None = None

    def describe(self):
        flag = ", with uncommitted edits" if self.uncommitted_edits else ""
        return f"{self.pin} is {self.commit} ({self.source.wording}{flag})"

    def to_json(self):
        return {
            "label": self.pin.label,
            "codeRepository": self.pin.repository,
            "name": self.pin.name,
            "kind": self.pin.kind,
            "value": self.pin.value,
            "commit": self.commit,
            "source": self.source.value,
            "uncommittedEdits": self.uncommitted_edits,
            "warning": self.warning,
            "path": optional_text(self.path),
            "adapter": optional_text(self.adapter),
            "report": optional_text(self.report),
        }

    @classmethod
    def from_json(cls, data):
        return cls(
            pin=Pin(data["label"], data["codeRepository"], data["kind"], data["value"]),
            commit=data["commit"],
            source=Source(data["source"]),
            uncommitted_edits=data["uncommittedEdits"],
            warning=data["warning"],
            path=optional_path(data["path"]),
            adapter=optional_path(data["adapter"]),
            report=optional_path(data["report"]),
        )


@dataclass
class Record:
    directory: Path
    mode: str
    pins: list[ResolvedPin] = field(default_factory=list)
    checked_out: bool = False

    @property
    def counterparts(self):
        return [entry for entry in self.pins if entry.pin.label == "mustPassWith"]

    def save(self, results):
        results.mkdir(parents=True, exist_ok=True)
        body = {
            "directory": str(self.directory),
            "mode": self.mode,
            "pins": [entry.to_json() for entry in self.pins],
            "checkedOut": self.checked_out,
        }
        (results / RECORD).write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, results):
        path = results / RECORD
        if not path.is_file():
            raise Stop(f"{path} is not there: run resolve or checkout first")
        data = read_json(path)
        return cls(
            directory=Path(data["directory"]),
            mode=data["mode"],
            pins=[ResolvedPin.from_json(entry) for entry in data["pins"]],
            checked_out=data["checkedOut"],
        )

    @classmethod
    def load_checked_out(cls, results):
        record = cls.load(results)
        if not record.checked_out:
            raise Stop("the record holds no checkout: run checkout first")
        return record
