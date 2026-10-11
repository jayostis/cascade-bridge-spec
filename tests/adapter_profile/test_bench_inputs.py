import copy
import hashlib
import json
import shutil

import pytest

import bench_inputs

MANIFEST = "bench/manifest.json"
INPUT = "bench/example-0001.xml.gz"


def with_member(name, value):
    def edit(manifest, package):
        manifest["inputs"][0][name] = value

    return edit


def without_member(name):
    def edit(manifest, package):
        del manifest["inputs"][0][name]

    return edit


def repeated(manifest, package):
    manifest["inputs"].append(copy.deepcopy(manifest["inputs"][0]))


def digest_of_the_file(manifest, package):
    manifest["inputs"][0]["sha256"] = hashlib.sha256((package.path / INPUT).read_bytes()).hexdigest()


def one_byte_off(manifest, package):
    manifest["inputs"][0]["bytes"] += 1


def a_gz_that_is_not_gzip(manifest, package):
    package.write("bench/plain.xml.gz", "plain text")
    manifest["inputs"][0]["path"] = "bench/plain.xml.gz"


REFUSED = {
    "measures missing": (without_member("measures"), "inputs[0].measures: is missing; wanted at least one"),
    "an id repeated": (repeated, "id synthetic-example-example-0001 appears 2 times; wanted each id once"),
    "an id without the crate's prefix": (
        with_member("id", "other-example-0001"),
        "id does not start with synthetic-example-, the crate's identifier and a hyphen",
    ),
    "a path to no file": (with_member("path", "bench/missing.xml.gz"), "path bench/missing.xml.gz is not a file"),
    "the sha256 of the gz file": (digest_of_the_file, "sha256 is not that of the bytes the measured thing is given"),
    "bytes off by one": (one_byte_off, "bytes is not the size of bench/example-0001.xml.gz gunzipped"),
    "an envelope naming no envelope": (
        with_member("envelope", "ro-crate-metadata.json#envelope-nothing"),
        "names no bridge:Envelope of the crate; wanted one of ro-crate-metadata.json#envelope-record, "
        "ro-crate-metadata.json#envelope-set",
    ),
    "onPullRequests yes": (
        with_member("onPullRequests", "yes"),
        "inputs[0].onPullRequests: 'yes' is not of type 'boolean'; wanted true or false",
    ),
    "a path with ..": (
        with_member("path", "bench/../bench/example-0001.xml.gz"),
        "inputs[0].path: 'bench/../bench/example-0001.xml.gz' should not be valid under",
    ),
    "a measure named timeout": (
        with_member("measures", ["convert", "timeout"]),
        "inputs[0].measures[1]: 'timeout' should not be valid under {'enum': ['timeout', 'refused']}; "
        "wanted at least one distinct lower-case segment, none of them timeout or refused",
    ),
    "a gz that is not gzip": (a_gz_that_is_not_gzip, "bench/plain.xml.gz is not a gzip file"),
}


def said_of(package, edit):
    manifest = json.loads((package.path / MANIFEST).read_text(encoding="utf-8"))
    edit(manifest, package)
    package.write(MANIFEST, json.dumps(manifest))
    return list(bench_inputs.faulty(package.crate))


def test_the_committed_synthetic_manifest_passes(crate):
    assert list(bench_inputs.faulty(crate)) == []


@pytest.mark.parametrize("edit, wanted", REFUSED.values(), ids=REFUSED.keys())
def test_a_manifest_fault_is_reported_with_what_was_wanted(package, edit, wanted):
    said = said_of(package, edit)
    assert any(wanted in message for message in said), said


def test_an_adapter_without_a_bench_manifest_gets_nothing(package):
    shutil.rmtree(package.path / "bench")
    assert list(bench_inputs.faulty(package.crate)) == []
