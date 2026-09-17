import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from compatibility_tool.console import Stop

RECORD = "record.json"


class Role(Enum):
    UNDER_TEST = "under test"
    SPECIFICATION = "specification"
    COUNTERPART = "counterpart"
    NOT_USED = "not used"


def optional_path(value):
    return None if value is None else Path(value)


def optional_text(value):
    return None if value is None else str(value)


@dataclass
class Used:
    name: str
    repository: str
    commit: str | None
    how: str
    role: Role
    uncommitted_edits: bool = False
    path: Path | None = None
    adapter: Path | None = None
    report: Path | None = None
    result: str | None = None
    holds: bool | None = None

    def describe(self):
        flag = ", with uncommitted edits" if self.uncommitted_edits else ""
        return f"{self.repository} is {self.commit} ({self.how}{flag})"

    def to_json(self):
        return {
            "repository": self.repository,
            "commit": self.commit,
            "how": self.how,
            "role": self.role.value,
            "uncommittedEdits": self.uncommitted_edits,
            "path": optional_text(self.path),
            "adapter": optional_text(self.adapter),
            "report": optional_text(self.report),
            "result": self.result,
            "holds": self.holds,
        }

    @classmethod
    def from_json(cls, name, data):
        return cls(
            name=name,
            repository=data["repository"],
            commit=data["commit"],
            how=data["how"],
            role=Role(data["role"]),
            uncommitted_edits=data["uncommittedEdits"],
            path=optional_path(data["path"]),
            adapter=optional_path(data["adapter"]),
            report=optional_path(data["report"]),
            result=data["result"],
            holds=data["holds"],
        )


@dataclass
class Record:
    directory: Path
    mode: str
    used: list[Used] = field(default_factory=list)

    @property
    def counterparts(self):
        return [entry for entry in self.used if entry.role is Role.COUNTERPART]

    def save(self, results):
        results.mkdir(parents=True, exist_ok=True)
        body = {
            "directory": str(self.directory),
            "mode": self.mode,
            "repositories": {entry.name: entry.to_json() for entry in self.used},
        }
        (results / RECORD).write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, results):
        path = Path(results) / RECORD
        if not path.is_file():
            raise Stop(f"{path} is not there: the run wrote no record")
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            directory=Path(data["directory"]),
            mode=data["mode"],
            used=[Used.from_json(name, entry) for name, entry in data["repositories"].items()],
        )
