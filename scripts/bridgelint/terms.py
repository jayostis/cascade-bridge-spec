"""The namespaces and the constants every check shares.

What each term means is its rdfs:comment in vocab/bridge.ttl; nothing is
restated here.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from rdflib import Namespace

BRIDGE = Namespace("https://ns.cascadeprotocol.org/bridge/v1-draft#")
SCHEMA = Namespace("http://schema.org/")
MF = Namespace("http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#")

SPEC_ROOT = Path(__file__).resolve().parent.parent.parent
SHAPES = SPEC_ROOT / "shapes" / "bridge.shapes.ttl"

# The files a repository holding an adapter may carry without the crate
# describing them: they describe the repository, not the package
# (adapter/validation.md). Dotfiles and dot-directories are allowed
# wholesale, which covers .gitattributes, .editorconfig, .vscode/ and .github/.
#
# ro-crate-metadata.json is here for a different reason from the other four. It
# is not undescribed: it is the crate's own metadata descriptor, the entity
# every RO-Crate is required to carry and the one entity RO-Crate 1.2 forbids
# from being a data entity in hasPart. It therefore has no encodingFormat and
# cannot be given one, so the inventory must name it here or fail every
# conforming crate.
ALLOWLIST = {
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "CLAUDE.md",
    "ro-crate-metadata.json",
}

# The local claim is schema:sha256 -- "sha256" in the RO-Crate 1.2
# context. Every other digest property is the publisher's claim about the file
# at its source, in whatever namespace it is written.
DIGEST_ALGORITHMS = {
    "md5": hashlib.md5,
    "sha1": hashlib.sha1,
    "sha256": hashlib.sha256,
    "sha384": hashlib.sha384,
    "sha512": hashlib.sha512,
}
LOCAL_DIGEST = SCHEMA.sha256

# XSD 1.0 by lxml is the only engine: v1-draft specifies XML sources.
XSD_MEDIA_TYPES = {"application/xml", "text/xml"}
JSON_SCHEMA_MEDIA_TYPES = {"application/json", "application/schema+json"}


def digest_of(path, algorithm):
    hasher = DIGEST_ALGORITHMS[algorithm]()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            hasher.update(block)
    return hasher.hexdigest()
