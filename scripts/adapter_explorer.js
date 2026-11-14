"use strict";
const index = JSON.parse(document.getElementById("search-index").textContent);
const box = document.getElementById("search");
const results = document.getElementById("results");
const SHOWN = 50;

function reveal(id) {
  const target = document.getElementById(id);
  if (!target) return;
  for (let node = target; node; node = node.parentElement) {
    if (node.tagName === "DETAILS") node.open = true;
  }
  target.scrollIntoView({ block: "start" });
}

function element(tag, text) {
  const made = document.createElement(tag);
  if (text !== undefined) made.textContent = text;
  return made;
}

addEventListener("hashchange", () => reveal(decodeURIComponent(location.hash.slice(1))));
if (location.hash) reveal(decodeURIComponent(location.hash.slice(1)));
document.addEventListener("click", (event) => {
  const anchor = event.target.closest('a[href^="#"]');
  if (anchor && anchor.getAttribute("href") === location.hash) reveal(location.hash.slice(1));
});

box.addEventListener("input", () => {
  const wanted = box.value.trim().toLowerCase();
  results.replaceChildren();
  results.hidden = wanted.length < 2;
  if (results.hidden) return;
  const found = index.filter((item) => item.text.includes(wanted));
  if (found.length === 0) {
    results.append(element("p", "No path or term matches."));
    return;
  }
  const list = element("ul");
  for (const item of found.slice(0, SHOWN)) {
    const entry = element("li");
    const anchor = element("a");
    anchor.href = "#" + item.node;
    anchor.append(element("code", item.place));
    entry.append(anchor);
    list.append(entry);
  }
  results.append(list);
  if (found.length > SHOWN) results.append(element("p", "More match: narrow the search."));
});

const ROLES = [
  ["input", "The input"],
  ["expectedGraph", "The graph expected"],
  ["expectedFindings", "The findings expected"],
];

document.addEventListener(
  "toggle",
  (event) => {
    const shown = event.target;
    if (!shown.classList || !shown.classList.contains("case") || !shown.open || shown.dataset.read) return;
    shown.dataset.read = "yes";
    const body = shown.querySelector(".case-body");
    body.textContent = "Reading the test case…";
    fetch(shown.dataset.file)
      .then((response) => {
        if (!response.ok) throw new Error(response.statusText);
        return response.json();
      })
      .then((testCase) => {
        body.replaceChildren();
        if (testCase.comment) body.append(element("p", testCase.comment));
        for (const [role, heading] of ROLES) {
          const file = testCase[role];
          if (!file) continue;
          const title = element("h4", heading + ", ");
          const anchor = element("a");
          anchor.href = file.link;
          anchor.append(element("code", file.file));
          title.append(anchor);
          const text = element("pre");
          text.append(element("code", file.text));
          body.append(title, text);
        }
      })
      .catch(() => {
        body.textContent = "The test case could not be read.";
      });
  },
  true,
);
