#!/usr/bin/env node
// Compares and lists result files of result.schema.json, whichever harness wrote them. No dependencies.
//
//   node compare.mjs compare <before.json> <after.json> [--name <glob>]
//   node compare.mjs history <directory | branch> --name <glob> [--since 7d] [--repository <git checkout>]
//   node compare.mjs merge <file.json>... > merged.json
//   node compare.mjs export <file.json> > benchmarks.json
//
// `compare` first reads each input's `<input>/output/*` digests. Where they differ the input is
// NOT EQUIVALENT: its rows show no change, and the exit status is 1. Where one side has no digest
// the input is UNVERIFIED, said and not failed. `history` reads a directory of result files, or a
// git branch of them (`bridge/YYYY/MM/DD/<run>-<sha7>.json`), newest last.
import { execFileSync } from "node:child_process";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const USAGE = `usage: node compare.mjs compare <before.json> <after.json> [--name <glob>]
       node compare.mjs history <directory | branch> --name <glob> [--since <n>h|<n>d|<n>w|<date>] [--repository <git checkout>]
       node compare.mjs merge <file.json>...
       node compare.mjs export <file.json>`;

class Refusal extends Error {}

function globbed(glob) {
  const pattern = glob
    .replace(/[.+^${}()|[\]\\]/g, "\\$&")
    .replaceAll("*", ".*")
    .replaceAll("?", ".");
  return new RegExp(`^${pattern}$`);
}

function flags(argv, known) {
  const positional = [];
  const named = {};
  for (let at = 0; at < argv.length; at++) {
    if (!argv[at].startsWith("--")) positional.push(argv[at]);
    else if (known.includes(argv[at]) && at + 1 < argv.length) named[argv[at].slice(2)] = argv[++at];
    else throw new Refusal(USAGE);
  }
  return { positional, named };
}

function readFile(path) {
  let file;
  try {
    file = JSON.parse(readFileSync(path, "utf8"));
  } catch (error) {
    throw new Refusal(`${path}: ${error.code ?? error.message}`);
  }
  if (!Array.isArray(file?.results)) throw new Refusal(`${path}: not a result file: it has no results`);
  return file;
}

function seconds(value) {
  return `${Number(value.toFixed(3)).toLocaleString("en", { maximumFractionDigits: 3 })} s`;
}

function shown(entry) {
  if (entry === undefined) return "—";
  if (entry.unit === "s") return seconds(entry.value);
  if (entry.unit === "By") return `${entry.value.toLocaleString("en")} B`;
  if (entry.unit === "{count}/s") return `${entry.value.toLocaleString("en", { maximumFractionDigits: 3 })}/s`;
  return entry.value.toLocaleString("en");
}

function percent(before, after) {
  if (before === 0) return after === 0 ? "0.0%" : "n/a";
  const change = ((after - before) / before) * 100;
  return `${change > 0 ? "+" : ""}${change.toFixed(1)}%`;
}

function multiple(before, after) {
  if (before === 0 || after === 0) return "n/a";
  return `${(before / after).toFixed(2)}×`;
}

function inputOf(name) {
  return name.split("/")[0];
}

// For each input that has digests on either side, what they say.
function equivalence(before, after) {
  const digests = (file) => {
    const found = new Map();
    for (const entry of file.results) {
      if (/^[^/]+\/output\/[^/]+$/.test(entry.name) && entry.sha256 !== undefined) found.set(entry.name, entry);
    }
    return found;
  }
  const [was, is] = [digests(before), digests(after)];
  const inputs = new Set([...was.keys(), ...is.keys()].map(inputOf));
  const verdicts = new Map();
  for (const input of inputs) {
    const names = [...new Set([...was.keys(), ...is.keys()])].filter((name) => inputOf(name) === input).sort();
    const differing = names.filter((name) => was.get(name)?.sha256 !== is.get(name)?.sha256);
    const unpaired = names.filter((name) => was.get(name) === undefined || is.get(name) === undefined);
    if (unpaired.length === names.length) {
      verdicts.set(input, { verdict: "UNVERIFIED", lines: [`${input}: the digests are on one side only`] });
    } else if (differing.length > 0) {
      verdicts.set(input, {
        verdict: "NOT EQUIVALENT",
        lines: differing.map(
          (name) =>
            `${name}: before ${was.get(name)?.value ?? "none"} quads, sha256 ${was.get(name)?.sha256 ?? "none"}; after ${is.get(name)?.value ?? "none"} quads, sha256 ${is.get(name)?.sha256 ?? "none"}`,
        ),
      });
    } else {
      verdicts.set(input, { verdict: "EQUIVALENT", lines: [] });
    }
  }
  return verdicts;
}

function machine(file) {
  const { env, commit } = file;
  return `${env.cpu ?? "unknown CPU"}, ${env.cpus} CPUs, ${env.os}, ${env.runner}, ${env.host}${env.node ? ` on Node ${env.node}` : ""}${env.otherLoad ? `, other load: ${env.otherLoad}` : ""}; ${Object.entries(commit)
    .map(([repository, sha]) => `${repository} ${sha.slice(0, 7)}${sha.endsWith("-dirty") ? "-dirty" : ""}`)
    .join(", ")}`;
}

function compare(argv) {
  const { positional, named } = flags(argv, ["--name"]);
  if (positional.length !== 2) throw new Refusal(USAGE);
  const [before, after] = positional.map(readFile);
  const only = named.name === undefined ? undefined : globbed(named.name);
  const verdicts = equivalence(before, after);
  const find = (file, name) => file.results.find((entry) => entry.name === name);
  const names = [...new Set([...before.results, ...after.results].map(({ name }) => name))].filter(
    (name) => only === undefined || only.test(name),
  );
  let said = `before: ${machine(before)}\nafter: ${machine(after)}\n`;
  if (machine({ ...before, commit: {} }) !== machine({ ...after, commit: {} }))
    said += "NOTE: the two files were written on different machines or settings; their times are not comparable.\n";
  said += "\n";
  let failed = false;
  for (const [input, { verdict, lines }] of verdicts) {
    if (verdict === "EQUIVALENT") continue;
    said += `${verdict} ${input}${verdict === "NOT EQUIVALENT" ? ": no speed-up is reported for it" : ""}\n`;
    for (const line of lines) said += `  ${line}\n`;
    if (verdict === "NOT EQUIVALENT") failed = true;
  }
  const equivalent = [...verdicts].filter(([, { verdict }]) => verdict === "EQUIVALENT").map(([input]) => input);
  if (equivalent.length > 0) said += `EQUIVALENT ${equivalent.join(", ")}: the output digests match\n`;
  said += "\n| name | before | after | change | multiple (before ÷ after) |\n|---|---|---|---|---|\n";
  for (const name of names) {
    const [was, is] = [find(before, name), find(after, name)];
    const blocked = verdicts.get(inputOf(name))?.verdict === "NOT EQUIVALENT" && !/\/output\//.test(name);
    if (was?.sha256 !== undefined || is?.sha256 !== undefined) {
      const same = was?.sha256 === is?.sha256;
      said += `| ${name} | ${shown(was)} | ${shown(is)} | ${same ? "same sha256" : "NOT EQUIVALENT"} | |\n`;
    } else if (was === undefined || is === undefined || was.unit !== is.unit) {
      said += `| ${name} | ${shown(was)} | ${shown(is)} | | |\n`;
    } else if (blocked) {
      said += `| ${name} | ${shown(was)} | ${shown(is)} | not compared | |\n`;
    } else {
      said += `| ${name} | ${shown(was)} | ${shown(is)} | ${percent(was.value, is.value)} | ${multiple(was.value, is.value)} |\n`;
    }
  }
  process.stdout.write(said);
  return failed ? 1 : 0;
}

function since(text) {
  if (text === undefined) return undefined;
  const relative = /^(\d+)([hdw])$/.exec(text);
  if (relative) return Date.now() - Number(relative[1]) * { h: 3600e3, d: 86400e3, w: 7 * 86400e3 }[relative[2]];
  const date = Date.parse(text);
  if (Number.isNaN(date)) throw new Refusal(`--since ${text}: not <n>h, <n>d, <n>w or a date`);
  return date;
}

function git(repository, ...args) {
  return execFileSync("git", ["-C", repository, ...args], {
    encoding: "utf8",
    maxBuffer: 1 << 30,
    stdio: ["ignore", "pipe", "pipe"],
  });
}

function directoryFiles(directory, prefix = "") {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) =>
    entry.isDirectory()
      ? directoryFiles(join(directory, entry.name), `${prefix}${entry.name}/`)
      : entry.name.endsWith(".json")
        ? [{ path: `${prefix}${entry.name}`, read: () => readFile(join(directory, entry.name)), mtime: statSync(join(directory, entry.name)).mtimeMs }]
        : [],
  );
}

// `<year>/<month>/<day>/<run>-<sha7>.json` anywhere in the path gives the day and run; a file elsewhere has its modification time.
function dated(files) {
  return files
    .map((file) => {
      const found = /(\d{4})\/(\d{2})\/(\d{2})\/(\d+)-([0-9a-f]+)\.json$/.exec(file.path);
      return found
        ? { ...file, time: Date.UTC(Number(found[1]), Number(found[2]) - 1, Number(found[3])), run: Number(found[4]), label: `${found[1]}-${found[2]}-${found[3]} #${found[4]} ${found[5]}` }
        : { ...file, time: file.mtime ?? 0, run: 0, label: file.path };
    })
    .sort((a, b) => a.time - b.time || a.run - b.run);
}

function branchFiles(repository, branch) {
  const ref = [branch, `origin/${branch}`].find((candidate) => {
    try {
      git(repository, "rev-parse", "--verify", "--quiet", candidate);
      return true;
    } catch {
      return false;
    }
  });
  if (ref === undefined) throw new Refusal(`${branch}: neither a directory nor a branch of ${repository}`);
  return git(repository, "ls-tree", "-r", "--name-only", ref)
    .split("\n")
    .filter((path) => path.endsWith(".json"))
    .map((path) => ({ path, read: () => JSON.parse(git(repository, "show", `${ref}:${path}`)) }));
}

function history(argv) {
  const { positional, named } = flags(argv, ["--name", "--since", "--repository"]);
  if (positional.length !== 1 || named.name === undefined) throw new Refusal(USAGE);
  const [source] = positional;
  const only = globbed(named.name);
  const from = since(named.since);
  let isDirectory = false;
  try {
    isDirectory = statSync(source).isDirectory();
  } catch {}
  const files = dated(isDirectory ? directoryFiles(source) : branchFiles(named.repository ?? ".", source)).filter(
    (file) => from === undefined || file.time >= from,
  );
  const rows = new Map();
  for (const file of files) {
    const result = file.read();
    for (const entry of result.results) {
      if (!only.test(entry.name)) continue;
      if (!rows.has(entry.name)) rows.set(entry.name, []);
      rows.get(entry.name).push({ label: file.label, entry, cpu: result.env?.cpu });
    }
  }
  let said = `${files.length} files${from === undefined ? "" : ` since ${new Date(from).toISOString().slice(0, 10)}`}\n`;
  for (const [name, points] of [...rows].sort(([a], [b]) => a.localeCompare(b))) {
    said += `\n${name}\n\n| file | value | range | change vs previous | sha256 |\n|---|---|---|---|---|\n`;
    points.forEach(({ label, entry }, index) => {
      const previous = points[index - 1]?.entry;
      const change =
        previous === undefined || previous.unit !== entry.unit
          ? ""
          : entry.sha256 !== undefined
            ? previous.sha256 === entry.sha256
              ? "same sha256"
              : "NOT EQUIVALENT to the previous"
            : percent(previous.value, entry.value);
      said += `| ${label} | ${shown(entry)} | ${entry.range ?? ""} | ${change} | ${entry.sha256?.slice(0, 12) ?? ""} |\n`;
    });
  }
  process.stdout.write(said);
  return 0;
}

// The files of one run, made by one harness on one machine, as one file: the first's env, every commit, every result.
function merge(argv) {
  if (argv.length === 0) throw new Refusal(USAGE);
  const files = argv.map(readFile);
  const names = files.flatMap((file) => file.results.map(({ name }) => name));
  const twice = names.find((name, index) => names.indexOf(name) !== index);
  if (twice !== undefined) throw new Refusal(`${twice} is in two of the files`);
  const merged = {
    env: files[0].env,
    commit: Object.assign({}, ...files.map((file) => file.commit)),
    results: files.flatMap((file) => file.results),
  };
  process.stdout.write(`${JSON.stringify(merged, null, 2)}
`);
  return 0;
}

// What github-action-benchmark's customSmallerIsBetter reads: one entry for each row worth a chart over time.
// The rows left out are exact counts that say little over time, and the failures, whose value is no measure.
const NOT_CHARTED = /\/(query-rows|output-bytes|memory\.grow|timeout|refused)\/|\/(index-built|load\/files-read|load\/missing-files)$/;

function exported(argv) {
  if (argv.length !== 1) throw new Refusal(USAGE);
  const charted = readFile(argv[0])
    .results.filter(({ name }) => !NOT_CHARTED.test(name))
    .map(({ name, unit, value, range, extra, sha256 }) => ({
      name,
      unit,
      value,
      ...(range === undefined ? {} : { range }),
      ...(extra === undefined && sha256 === undefined
        ? {}
        : { extra: [extra, sha256 === undefined ? undefined : `sha256 ${sha256}`].filter(Boolean).join(" ") }),
    }));
  process.stdout.write(`${JSON.stringify(charted, null, 2)}
`);
  return 0;
}

try {
  const [command, ...rest] = process.argv.slice(2);
  if (command === "compare") process.exitCode = compare(rest);
  else if (command === "history") process.exitCode = history(rest);
  else if (command === "merge") process.exitCode = merge(rest);
  else if (command === "export") process.exitCode = exported(rest);
  else throw new Refusal(USAGE);
} catch (error) {
  process.stderr.write(`compare: ${error instanceof Error ? error.message : String(error)}\n`);
  process.exitCode = 2;
}
