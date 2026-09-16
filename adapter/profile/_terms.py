from __future__ import annotations

import hashlib
from pathlib import Path

from rdflib import Namespace

BRIDGE = Namespace("https://ns.cascadeprotocol.org/bridge/v1-draft#")
SCHEMA = Namespace("http://schema.org/")
MF = Namespace("http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#")

SPEC_ROOT = Path(__file__).resolve().parent.parent.parent
SHAPES = SPEC_ROOT / "shapes" / "bridge.shapes.ttl"

FILES_THE_CRATE_NEED_NOT_DESCRIBE = {
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "CLAUDE.md",
    "ro-crate-metadata.json",
}

DIGEST_ALGORITHMS = {
    "md5": hashlib.md5,
    "sha1": hashlib.sha1,
    "sha256": hashlib.sha256,
    "sha384": hashlib.sha384,
    "sha512": hashlib.sha512,
}
LOCAL_DIGEST = SCHEMA.sha256

XSD_MEDIA_TYPES = {"application/xml", "text/xml"}
JSON_SCHEMA_MEDIA_TYPES = {"application/json", "application/schema+json"}


def digest_of(path, algorithm):
    hasher = DIGEST_ALGORITHMS[algorithm]()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            hasher.update(block)
    return hasher.hexdigest()
