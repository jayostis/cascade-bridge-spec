import json
import subprocess
from pathlib import Path

COMPARE = Path(__file__).resolve().parents[2] / "bench" / "compare.mjs"
SHA = "a" * 64
OTHER_SHA = "b" * 64


def result(convert, graph_sha=SHA, **env):
    return {
        "env": {
            "os": "Linux",
            "runner": "local",
            "cpus": 4,
            "cpu": "A CPU",
            "node": "24.16.0",
            "host": "node",
            "profile": "wasm",
            **env,
        },
        "commit": {"an-engine": "0123456789abcdef0123456789abcdef01234567"},
        "results": [
            {
                "name": "x10/convert/first",
                "unit": "s",
                "value": convert,
                "kind": "clock",
                "samples": 1,
                "range": f"{convert}-{convert}",
            },
            {"name": "x10/triples", "unit": "{count}", "value": 100, "kind": "output"},
            {"name": "x10/output/graph", "unit": "{count}", "value": 100, "kind": "output", "sha256": graph_sha},
        ]
        if graph_sha
        else [
            {
                "name": "x10/convert/first",
                "unit": "s",
                "value": convert,
                "kind": "clock",
                "samples": 1,
                "range": f"{convert}-{convert}",
            },
        ],
    }


def written(directory, name, document):
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def run(*arguments, cwd=None):
    return subprocess.run(
        ["node", str(COMPARE), *map(str, arguments)], capture_output=True, text=True, encoding="utf-8", cwd=cwd
    )


class TestComparingAndListingResultFiles:
    """Comparing and listing result files · bench/compare.mjs

    `compare` sets two result files side by side with the change and the multiple of each row, and reads the output
    digests first: an input whose digests differ is not equivalent, and is given no speed-up. `history` lists a
    named result across the files of a directory or of a git branch.
    """

    class TestCompare:
        """`compare`"""

        def test_prints_the_change_and_the_multiple_of_a_row_whose_output_is_the_same(self, tmp_path):
            before, after = written(tmp_path, "a.json", result(10.0)), written(tmp_path, "b.json", result(4.0))
            run_ = run("compare", before, after)
            assert run_.returncode == 0, run_.stderr
            assert "| x10/convert/first | 10 s | 4 s | -60.0% | 2.50× |" in run_.stdout
            assert "EQUIVALENT x10" in run_.stdout

        def test_exits_1_and_reports_no_speed_up_for_an_input_whose_digests_differ(self, tmp_path):
            before, after = (
                written(tmp_path, "a.json", result(10.0)),
                written(tmp_path, "b.json", result(4.0, OTHER_SHA)),
            )
            run_ = run("compare", before, after)
            assert run_.returncode == 1
            assert "NOT EQUIVALENT x10" in run_.stdout
            assert "| x10/convert/first | 10 s | 4 s | not compared | |" in run_.stdout
            assert "2.50" not in run_.stdout

        def test_says_unverified_and_does_not_fail_where_one_side_has_no_digest(self, tmp_path):
            before, after = (
                written(tmp_path, "a.json", result(10.0, graph_sha=None)),
                written(tmp_path, "b.json", result(4.0)),
            )
            run_ = run("compare", before, after)
            assert run_.returncode == 0
            assert "UNVERIFIED x10" in run_.stdout

        def test_says_that_the_times_of_two_machines_are_not_comparable(self, tmp_path):
            before, after = (
                written(tmp_path, "a.json", result(10.0)),
                written(tmp_path, "b.json", result(4.0, cpu="Another CPU")),
            )
            assert "not comparable" in run("compare", before, after).stdout

        def test_keeps_only_the_rows_a_name_glob_matches(self, tmp_path):
            before, after = written(tmp_path, "a.json", result(10.0)), written(tmp_path, "b.json", result(4.0))
            said = run("compare", before, after, "--name", "*/triples").stdout
            assert "x10/triples" in said and "x10/convert/first |" not in said

        def test_exits_2_on_a_file_that_is_not_a_result_file(self, tmp_path):
            junk = written(tmp_path, "junk.json", {"hello": 1})
            assert run("compare", junk, junk).returncode == 2

    class TestHistory:
        """`history`"""

        def test_lists_a_name_across_the_files_of_a_directory_newest_last_from_the_day_in_their_paths(self, tmp_path):
            written(tmp_path, "bridge/2026/11/19/7-bbbbbbb.json", result(4.0))
            written(tmp_path, "bridge/2026/11/18/3-aaaaaaa.json", result(10.0))
            said = run("history", tmp_path, "--name", "x10/convert/first").stdout
            assert said.index("2026-11-18 #3 aaaaaaa") < said.index("2026-11-19 #7 bbbbbbb")
            assert "-60.0%" in said

        def test_leaves_out_the_files_older_than_since(self, tmp_path):
            written(tmp_path, "bridge/2001/01/01/1-aaaaaaa.json", result(10.0))
            written(tmp_path, "bridge/2099/01/01/2-bbbbbbb.json", result(4.0))
            said = run("history", tmp_path, "--name", "x10/*", "--since", "7d").stdout
            assert "2001-01-01" not in said and "2099-01-01" in said

        def test_reads_the_files_of_a_branch(self, tmp_path):

            def git(*arguments):
                subprocess.run(["git", "-C", str(tmp_path), *arguments], check=True, capture_output=True)

            git("init", "-q", "-b", "perf-data")
            written(tmp_path, "bridge/2026/11/18/3-aaaaaaa.json", result(10.0))
            git("add", ".")
            git("-c", "user.name=t", "-c", "user.email=t@example.org", "commit", "-q", "-m", "a result")
            said = run("history", "perf-data", "--name", "x10/convert/first", "--repository", tmp_path).stdout
            assert "2026-11-18 #3 aaaaaaa" in said

    class TestMerge:
        """`merge`"""

        def test_writes_the_results_and_the_commits_of_each_file_as_one_file(self, tmp_path):
            first, second = result(10.0), result(4.0)
            second["results"] = [{**entry, "name": entry["name"].replace("x10", "x50")} for entry in second["results"]]
            second["commit"] = {"an-adapter": "89abcdef0123456789abcdef0123456789abcdef"}
            run_ = run("merge", written(tmp_path, "a.json", first), written(tmp_path, "b.json", second))
            merged = json.loads(run_.stdout)
            assert len(merged["results"]) == 6
            assert sorted(merged["commit"]) == ["an-adapter", "an-engine"]

        def test_refuses_two_files_that_both_hold_a_name(self, tmp_path):
            path = written(tmp_path, "a.json", result(10.0))
            assert run("merge", path, path).returncode == 2
