"use strict";
document.documentElement.classList.add("js");
const index = JSON.parse(document.getElementById("search-index").textContent);
const tree = document.getElementById("tree");
const box = document.getElementById("search");
const count = document.getElementById("count");
const narrowed = document.getElementById("narrowed");
const panes = document.querySelector(".panes");
const casePane = document.getElementById("case");
const tabs = document.getElementById("tabs");
const narrow = matchMedia("(max-width: 760px)");
const measureBar = () =>
  document.documentElement.style.setProperty("--bar", `${narrow.matches ? tabs.offsetHeight : 0}px`);
measureBar();
new ResizeObserver(measureBar).observe(tabs);
narrow.addEventListener("change", measureBar);

function element(tag, text, className) {
  const made = document.createElement(tag);
  if (text !== undefined) made.textContent = text;
  if (className) made.className = className;
  return made;
}

function show(pane) {
  for (const tab of tabs.querySelectorAll("button")) {
    const on = tab.getAttribute("aria-controls") === pane;
    tab.classList.toggle("on", on);
    if (on) tab.setAttribute("aria-current", "true");
    else tab.removeAttribute("aria-current");
    document.getElementById(tab.getAttribute("aria-controls")).classList.toggle("on", on);
  }
  if (!narrow.matches) return;
  const top = panes.getBoundingClientRect().top + scrollY - tabs.offsetHeight;
  if (scrollY > top) scrollTo(0, top);
  if (pane === "case-pane") for (const text of casePane.querySelectorAll("pre")) toMark(text);
}
tabs.addEventListener("click", (event) => {
  const tab = event.target.closest("button");
  if (tab) show(tab.getAttribute("aria-controls"));
});

function shownView() {
  const id = decodeURIComponent(location.hash.slice(1));
  const target = id && document.getElementById(id);
  return target && target.classList.contains("view") ? target : document.getElementById("overview");
}

function select(moved, focus) {
  const view = shownView();
  for (const stop of document.querySelectorAll(".stop")) {
    const on = stop.getAttribute("href") === "#" + view.dataset.stop;
    stop.classList.toggle("on", on);
    if (on) stop.setAttribute("aria-current", "true");
    else stop.removeAttribute("aria-current");
  }
  tabs.querySelector('[aria-controls="views-pane"]').textContent = view.querySelector("h2.ph").textContent;
  for (const row of tree.querySelectorAll(".row.sel")) row.classList.remove("sel");
  for (const link of tree.querySelectorAll("[aria-current]")) link.removeAttribute("aria-current");
  const detail = view.classList.contains("detail");
  const row = detail && tree.querySelector(`[data-node="${view.id}"]`);
  if (row) {
    for (let at = row.parentElement; at && at !== tree; at = at.parentElement) {
      if (at.tagName === "DETAILS") at.open = true;
    }
    row.classList.add("sel");
    (row.matches("a") ? row : row.querySelector("a.nm")).setAttribute("aria-current", "true");
    if (!narrow.matches) row.scrollIntoView({ block: "nearest" });
  }
  if (detail) {
    const first = view.querySelector("[data-case]");
    if (first) load(first);
    else {
      loaded = null;
      casePane.replaceChildren(element("p", "No test case of the adapter shows this place.", "empty"));
    }
    panes.classList.toggle("with-case", Boolean(first));
  } else if (view.id !== "cases") panes.classList.remove("with-case");
  if (moved && narrow.matches) {
    show(view.id === "paths" ? "paths-pane" : "views-pane");
    if (view.id !== "paths") view.scrollIntoView({ block: "start" });
  }
  const heading = view.querySelector("h1");
  if (focus && heading.offsetParent) heading.focus({ preventScroll: narrow.matches });
}

const narrowing = { text: "", concern: "", verdict: "", nodes: null };

function apply() {
  const wanted = narrowing.text.length >= 2 ? narrowing.text : "";
  const active = wanted || narrowing.concern || narrowing.verdict || narrowing.nodes;
  const matched = wanted && new Set(index.filter((item) => item.text.includes(wanted)).map((item) => item.node));
  const kept = new Set();
  const opened = new Set();
  let found = 0;
  const rows = tree.querySelectorAll("[data-node]");
  if (active) {
    for (const row of rows) {
      const id = row.dataset.node;
      const hit =
        (!matched || matched.has(id)) &&
        (!narrowing.concern || row.dataset.c.split(" ").includes(narrowing.concern)) &&
        (!narrowing.verdict || row.dataset.v.split(" ").includes(narrowing.verdict)) &&
        (!narrowing.nodes || narrowing.nodes.has(id));
      if (!hit) continue;
      found += 1;
      const own = row.closest("li");
      for (let item = own; item; item = item.parentElement.closest("li")) {
        kept.add(item);
        if (item !== own) opened.add(item);
      }
    }
  }
  for (const row of rows) {
    const item = row.closest("li");
    item.hidden = Boolean(active) && !kept.has(item);
    if (opened.has(item)) item.querySelector(":scope > details").open = true;
  }
  if (active && !narrow.matches) tree.parentElement.scrollTop = 0;
  if (!active) count.textContent = "";
  else if (found === 0) count.textContent = "No path or term matches.";
  else count.textContent = found === 1 ? "1 place matches." : found + " places match.";
}

box.addEventListener("input", () => {
  narrowing.text = box.value.trim().toLowerCase();
  apply();
});

function narrowTo(label, verdict, nodes) {
  Object.assign(narrowing, { verdict, nodes });
  narrowed.hidden = false;
  narrowed.textContent = label + " ×";
  narrowed.setAttribute("aria-label", "Showing " + label + ": show every path again");
  apply();
  if (narrow.matches) show("paths-pane");
}
narrowed.addEventListener("click", () => {
  Object.assign(narrowing, { verdict: "", nodes: null });
  narrowed.hidden = true;
  apply();
});

function byConcern(concern) {
  narrowing.concern = concern;
  for (const chip of document.querySelectorAll("#paths-pane [data-concern]")) {
    const on = chip.dataset.concern === concern;
    chip.classList.toggle("on", on);
    chip.setAttribute("aria-pressed", String(on));
  }
  apply();
}

addEventListener("hashchange", () => select(true, true));
document.addEventListener("click", (event) => {
  const anchor = event.target.closest('a[href^="#"]');
  if (anchor && anchor.getAttribute("href") === location.hash) select(true, true);
  const name = event.target.closest("summary a.nm");
  if (name && narrow.matches && !name.closest(".row").hasAttribute("data-own")) {
    event.preventDefault();
    const folder = name.closest("details");
    folder.open = !folder.open;
    return;
  }
  const concern = event.target.closest("[data-concern]");
  if (concern) {
    byConcern(concern.dataset.concern);
    if (narrow.matches) show("paths-pane");
    return;
  }
  const verdict = event.target.closest("tr[data-verdict]");
  if (verdict) {
    narrowTo(verdict.querySelector(".v").textContent, verdict.dataset.verdict, null);
    return;
  }
  const reason = event.target.closest("[data-nodes]");
  if (reason) {
    narrowTo(reason.textContent, "", new Set(reason.dataset.nodes.split(" ")));
    return;
  }
  const testCase = event.target.closest("a[data-case]");
  if (testCase) {
    event.preventDefault();
    load(testCase);
    panes.classList.add("with-case");
    if (narrow.matches) show("case-pane");
  }
});

const ROLES = [
  ["input", "The input", "1"],
  ["expectedGraph", "The graph expected", "2"],
  ["expectedFindings", "The findings expected", "1"],
];
const SAID = {
  1: "where a finding this path raises points in the input, and the finding",
  2: "the property this path becomes, wherever the graph expected has it",
};
let loaded = null;

function load(link) {
  const marks = JSON.parse(link.dataset.marks || "{}");
  const wanted = link.dataset.case + " " + link.dataset.marks;
  if (wanted === loaded) return;
  loaded = wanted;
  casePane.replaceChildren(element("p", "Reading the test case…", "empty"));
  fetch(link.dataset.case)
    .then((response) => {
      if (!response.ok) throw new Error(response.statusText);
      return response.json();
    })
    .then((testCase) => {
      if (loaded !== wanted) return;
      casePane.replaceChildren(...shownCase(testCase, marks));
      for (const text of casePane.querySelectorAll("pre")) toMark(text);
    })
    .catch(() => {
      if (loaded === wanted) casePane.replaceChildren(element("p", "The test case could not be read.", "empty"));
    });
}

function shownCase(testCase, marks) {
  const head = element("div", undefined, "casehead");
  head.append(element("b", testCase.name));
  if (testCase.comment) head.append(element("p", testCase.comment, "fx"));
  const body = element("div", undefined, "casebody");
  const numbers = new Set();
  for (const [role, heading, number] of ROLES) {
    const file = testCase[role];
    if (!file) continue;
    const where = element("a");
    where.href = file.link;
    where.append(element("code", file.file));
    if (file.empty) {
      const none = element("p", "This case expects no findings: ");
      none.append(where, ".");
      body.append(none);
      continue;
    }
    const title = element("h4", heading + " · ");
    title.append(where);
    const marked = new Set(marks[role] || []);
    if (marked.size) numbers.add(number);
    body.append(title, lines(file.text, marked, number));
  }
  if (numbers.size) {
    const notes = element("ol", undefined, "notes");
    for (const number of [...numbers].sort()) {
      const note = element("li");
      note.append(element("b", number, "num"), element("span", SAID[number]));
      notes.append(note);
    }
    body.append(notes);
  }
  return [head, body];
}

function lines(text, marked, number) {
  const shown = element("pre");
  let run = [];
  const flush = () => {
    if (run.length) shown.append(run.join("\n") + "\n");
    run = [];
  };
  text.split("\n").forEach((line, at) => {
    if (!marked.has(at + 1)) {
      run.push(line);
      return;
    }
    flush();
    const mark = element("span", undefined, "hl");
    mark.append(element("b", number, "num"), line + "\n");
    shown.append(mark);
  });
  flush();
  return shown;
}

function toMark(text) {
  const mark = text.querySelector(".hl");
  if (mark && text.clientHeight) text.scrollTop = Math.max(0, mark.offsetTop - text.clientHeight / 3);
}

select(Boolean(location.hash));
