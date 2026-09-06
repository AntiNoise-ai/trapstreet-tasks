/**
 * The check half of the judge: given one HTML page, drive it in a real browser
 * and report what broke.
 *
 * Usage:  node inspect.mjs <page.html> <spec.json> <out-dir>
 * Emits one JSON object on stdout. Never throws for a page-level failure —
 * a page that will not load is a result, not a crash.
 *
 * Four check families. Only three of them are meant to decide a score; see
 * README for why contrast/labels are diagnostics.
 */
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";
import { pathToFileURL } from "node:url";
import puppeteer from "puppeteer-core";

const require = createRequire(import.meta.url);
const AXE_SOURCE = require("fs").readFileSync(
  require.resolve("axe-core/axe.min.js"), "utf8");

const CHROME = process.env.CHROME_PATH ||
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const DESKTOP = { width: 1280, height: 960 };
const PHONE = { width: 375, height: 812 };

/* ---------- the assertion DSL ---------------------------------------- */

async function runSteps(page, steps = []) {
  for (const s of steps) {
    if (s.action === "click") {
      const el = await page.$(s.selector);
      if (!el) return `no element matches ${s.selector}`;
      await el.click();
    } else if (s.action === "type") {
      const el = await page.$(s.selector);
      if (!el) return `no element matches ${s.selector}`;
      await el.type(s.text ?? "");
    } else if (s.action === "viewport") {
      await page.setViewport(s.size === "phone" ? PHONE : DESKTOP);
    } else if (s.action === "wait") {
      await new Promise(r => setTimeout(r, s.ms ?? 150));
    }
  }
  return null;
}

async function readProbe(page, probe) {
  return page.evaluate((p) => {
    const els = [...document.querySelectorAll(p.selector)];
    const el = els[p.nth ?? 0];
    if (!el) return { missing: true, count: els.length };
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return {
      missing: false,
      count: els.length,
      text: (el.innerText || el.textContent || "").trim(),
      visible: r.width > 0 && r.height > 0 &&
               cs.visibility !== "hidden" && cs.display !== "none" &&
               Number(cs.opacity) > 0.01,
      rect: { x: r.x, y: r.y, w: r.width, h: r.height },
    };
  }, probe);
}

/** One behaviour assertion: read probes, run steps, read again, compare. */
async function checkBehaviour(page, a) {
  const before = {};
  for (const e of a.expect ?? []) {
    if (e.textChanged || e.textUnchanged) before[e.selector + (e.nth ?? 0)] = await readProbe(page, e);
  }
  const stepErr = await runSteps(page, a.steps);
  if (stepErr) return { name: a.name, ok: false, why: stepErr };

  for (const e of a.expect ?? []) {
    const got = await readProbe(page, e);
    const key = e.selector + (e.nth ?? 0);
    if (e.exists !== undefined && got.missing === e.exists)
      return { name: a.name, ok: false, why: `${e.selector} exists=${!got.missing}, wanted ${e.exists}`, rect: got.rect };
    if (got.missing && e.exists !== false)
      return { name: a.name, ok: false, why: `${e.selector} not found` };
    if (e.count !== undefined && got.count !== e.count)
      return { name: a.name, ok: false, why: `${e.selector} matched ${got.count}, wanted ${e.count}` };
    if (e.visible !== undefined && got.visible !== e.visible)
      return { name: a.name, ok: false, why: `${e.selector} visible=${got.visible}, wanted ${e.visible}`, rect: got.rect };
    if (e.textMatches && !new RegExp(e.textMatches, "i").test(got.text))
      return { name: a.name, ok: false, why: `${e.selector} text ${JSON.stringify(got.text.slice(0, 60))} !~ /${e.textMatches}/`, rect: got.rect };
    if (e.textChanged && before[key] && before[key].text === got.text)
      return { name: a.name, ok: false, why: `${e.selector} text did not change (${JSON.stringify(got.text.slice(0, 40))})`, rect: got.rect };
    if (e.textUnchanged && before[key] && before[key].text !== got.text)
      return { name: a.name, ok: false, why: `${e.selector} text changed but should not have`, rect: got.rect };
  }
  return { name: a.name, ok: true };
}

/* ---------- families ------------------------------------------------- */

/** Horizontal overflow at 375px — the container that sticks out, and by how much. */
async function checkResponsive(page, want = {}) {
  const width = want.width ?? PHONE.width;
  await page.setViewport({ width, height: want.height ?? PHONE.height });
  await new Promise(r => setTimeout(r, 120));
  const out = await page.evaluate(() => {
    const doc = document.documentElement;
    const overflow = doc.scrollWidth - doc.clientWidth;
    const culprits = [];
    if (overflow > 1) {
      for (const el of document.querySelectorAll("body *")) {
        const r = el.getBoundingClientRect();
        if (r.width === 0) continue;
        if (r.right > doc.clientWidth + 1 || r.left < -1) {
          culprits.push({
            tag: el.tagName.toLowerCase(),
            over: Math.round(Math.max(r.right - doc.clientWidth, -r.left)),
            rect: { x: r.x, y: r.y, w: r.width, h: r.height },
          });
        }
      }
    }
    culprits.sort((a, b) => b.over - a.over);
    return { overflow: Math.round(overflow), culprits: culprits.slice(0, 4) };
  });
  out.width = width;
  await page.setViewport(DESKTOP);
  return out;
}

/**
 * Robustness: re-render the page against hostile data and see if it survives.
 * The brief requires the page to read window.__DATA__, so the judge can swap it.
 */
/* ---------- hostile payload generation ------------------------------- *
 * A hand-written list of payloads has a ceiling the author can see: ours was
 * thirteen, and three frontier arms took 13/13. A generator does not have that
 * ceiling, cannot be memorised, and cannot be targeted case by case.
 *
 * Seeded, so a run is reproducible and two arms get byte-identical payloads.
 * The recipe crossing the process boundary is JSON-safe; the hostile values
 * themselves are built inside the page, because `undefined`, `NaN`, cyclic
 * objects and lone surrogates do not survive serialisation.
 */

// mulberry32 — small, seeded, and identical across platforms.
function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const ATOM_NAMES = [
  "empty", "spaces", "newlines", "long240", "long4000", "wideCJK", "zwj",
  "rtlOverride", "combining", "zeroWidth", "loneSurrogate",
  "htmlScript", "htmlImg", "htmlBreakout", "templateExpr", "mustache",
  "nullish", "undef", "nan", "numZero", "numNeg", "numHuge", "numFloat",
  "boolTrue", "emptyArr", "emptyObj", "deepNest", "cyclic", "numericString",
];
// Injection atoms: a page that lets one of these run has failed in a way no
// amount of partial credit should soften. See `blocker` below.
const INJECTION = new Set(["htmlScript", "htmlImg", "htmlBreakout", "mustache", "templateExpr"]);

const COUNTS = [0, 1, 2, 3, 7, 25];

/** Build the variant list. Returns the same shape the static `robustness`
 *  spec produces, so downstream code does not care where a variant came from. */
function generateVariants(gen) {
  const rand = rng(gen.seed ?? 1);
  const pick = (xs) => xs[Math.floor(rand() * xs.length)];
  const fields = gen.fields ?? ["name", "monthly", "features"];
  const n = gen.n ?? 40;
  const out = [];
  const seen = new Set();

  while (out.length < n) {
    const kind = pick(["field", "field", "field", "drop", "count", "whole", "pollute", "nest"]);
    let mutations, name;
    if (kind === "field") {
      const i = Math.floor(rand() * 3), f = pick(fields), atom = pick(ATOM_NAMES);
      mutations = [{ op: "field", index: i, field: f, atom }];
      name = `plans[${i}].${f} = ${atom}`;
    } else if (kind === "drop") {
      const i = Math.floor(rand() * 3), f = pick(fields);
      mutations = [{ op: "drop", index: i, field: f }];
      name = `plans[${i}] has no ${f}`;
    } else if (kind === "count") {
      const c = pick(COUNTS);
      mutations = [{ op: "count", n: c }];
      name = `${c} plan(s)`;
    } else if (kind === "whole") {
      const atom = pick(ATOM_NAMES);
      mutations = [{ op: "whole", atom }];
      name = `__DATA__ is ${atom}, not an array`;
    } else if (kind === "pollute") {
      mutations = [{ op: "pollute" }];
      name = "__proto__ injected into a plan";
    } else {
      const i = Math.floor(rand() * 3);
      mutations = [{ op: "nest", index: i }];
      name = `plans[${i}].features is nested three deep`;
    }
    if (seen.has(name)) continue;
    seen.add(name);

    const v = {
      name,
      recipe: { base: gen.base ?? [], mutations },
      selector: gen.selector ?? "*[data-testid]",
      forbidSelector: gen.forbidSelector ?? "[data-ghost], [data-testid=tier] script",
      generated: true,
    };
    // Only a count mutation leaves the payload well-formed enough to predict
    // how many cards should render. Everything else keeps the universal checks
    // (does not throw, does not overflow, renders something, executes nothing)
    // and asserts nothing about the count.
    if (kind === "count") v.expectCount = mutations[0].n;
    if (mutations.some(m => INJECTION.has(m.atom))) v.injection = true;
    out.push(v);
  }
  return out;
}

/** Materialise a recipe inside the page. Runs as a string in page context. */
function materialise(recipe) {
  const A = {
    empty: "", spaces: "   ", newlines: "\n\n\t",
    long240: "L".repeat(240), long4000: "L".repeat(4000),
    wideCJK: "廣".repeat(200),
    zwj: "\u{1F468}‍\u{1F469}‍\u{1F467}".repeat(30),
    rtlOverride: "‮eman-live",
    combining: "a" + "́".repeat(300),
    zeroWidth: "​".repeat(400),
    loneSurrogate: "ok\uD800tail",
    htmlScript: "<scr" + "ipt>window.__pwned=1</scr" + "ipt>",
    htmlImg: '<img src=x onerror="window.__pwned=1">',
    htmlBreakout: '</div><div data-testid="tier" data-ghost="1">ghost</div>',
    templateExpr: "${window.__pwned=1}",
    mustache: "{{constructor.constructor('window.__pwned=1')()}}",
    nullish: null, undef: undefined, nan: NaN,
    numZero: 0, numNeg: -1, numHuge: 1e21, numFloat: 0.30000000000000004,
    boolTrue: true, emptyArr: [], emptyObj: {},
    numericString: "12",
    get deepNest() { let o = {}, c = o; for (let i = 0; i < 60; i++) { c.n = {}; c = c.n; } return o; },
    get cyclic() { const o = { name: "loop" }; o.self = o; return o; },
  };
  let data = JSON.parse(JSON.stringify(recipe.base));
  for (const m of recipe.mutations) {
    if (m.op === "whole") { data = A[m.atom]; break; }
    if (m.op === "count") {
      const proto = recipe.base[0] ?? { name: "Plan", monthly: 9, features: ["A"] };
      data = Array.from({ length: m.n }, (_, i) =>
        ({ ...JSON.parse(JSON.stringify(proto)), name: `${proto.name} ${i + 1}` }));
      continue;
    }
    if (!Array.isArray(data) || !data[m.index]) continue;
    if (m.op === "field") data[m.index][m.field] = A[m.atom];
    else if (m.op === "drop") delete data[m.index][m.field];
    else if (m.op === "nest") data[m.index].features = [[[data[m.index].features]]];
    else if (m.op === "pollute") data[m.index]["__proto__"] = { polluted: 1 };
  }
  return data;
}

async function checkRobustness(browser, url, variants) {
  const results = [];
  for (const v of variants) {
    const page = await browser.newPage();      // fresh page: no script build-up
    const errors = [];
    page.on("pageerror", e => errors.push(String(e).slice(0, 120)));
    await page.setViewport(v.viewport === "phone" ? PHONE : DESKTOP);
    if (v.recipe) {
      await page.evaluateOnNewDocument((recipe, src) => {
        // eslint-disable-next-line no-new-func
        window.__DATA__ = new Function("recipe", `return (${src})(recipe)`)(recipe);
      }, v.recipe, materialise.toString());
    } else {
      await page.evaluateOnNewDocument((data) => { window.__DATA__ = data; }, v.data);
    }
    let out, loadErr = null;
    try {
      await page.goto(url, { waitUntil: "load", timeout: 15000 });
      await new Promise(r => setTimeout(r, 150));
      out = await page.evaluate((sel, forbid) => {
        const doc = document.documentElement;
        const els = [...document.querySelectorAll(sel)];
        // Content that does not fit is only a defect when it vanishes WITHOUT an
        // affordance. A deliberate line-clamp with an ellipsis, or a title/aria
        // label carrying the full string, is correct handling — not a failure.
        // (Learned the hard way: the first real run flagged exactly that as a bug.)
        let clipped = 0;
        for (const el of els) {
          const over = el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1;
          if (!over) continue;
          const cs = getComputedStyle(el);
          const affordance =
            cs.webkitLineClamp && cs.webkitLineClamp !== "none" ||
            cs.textOverflow === "ellipsis" ||
            el.hasAttribute("title") || el.hasAttribute("aria-label") ||
            el.closest("[title],[aria-label]") !== null;
          if (!affordance) clipped++;
        }
        return {
          overflow: Math.round(doc.scrollWidth - doc.clientWidth),
          count: els.length,
          clipped,
          bodyText: (document.body.innerText || "").trim().length,
          forbidden: forbid ? document.querySelectorAll(forbid).length : 0,
          pwned: window.__pwned !== undefined,
          title: document.title,
        };
      }, v.selector ?? "*[data-testid]", v.forbidSelector ?? null);
    } catch (e) {
      loadErr = String(e).slice(0, 120);
    }

    const fails = [];
    if (loadErr) fails.push(`page failed: ${loadErr}`);
    else {
      if (out.overflow > 1) fails.push(`overflows by ${out.overflow}px`);
      if (out.clipped > 0) fails.push(`${out.clipped} element(s) silently cut their content — no ellipsis, no title`);
      if (v.expectCount !== undefined && out.count !== v.expectCount)
        fails.push(`rendered ${out.count} cards, expected ${v.expectCount}`);
      if (v.expectNonEmpty !== false && out.bodyText === 0)
        fails.push("page rendered nothing at all");
      if (out.forbidden > 0) fails.push(`injected markup became ${out.forbidden} live element(s)`);
      if (out.pwned) fails.push("injected code EXECUTED (window.__pwned is set)");
      if (v.expectTitle !== undefined && out.title !== v.expectTitle)
        fails.push(`document.title is now ${JSON.stringify(out.title)}`);
    }
    if (errors.length) fails.push(`threw: ${errors[0]}`);

    // A page that executes injected content has failed in a way partial credit
    // must not soften — this is the blocker, in FrontierCode's sense.
    const breached = !loadErr && out && (out.pwned || out.forbidden > 0);
    results.push({
      name: v.name, ok: fails.length === 0,
      why: fails.length ? fails.join("; ") : null,
      ...(breached ? { blocker: true } : {}),
      ...(v.generated ? { generated: true } : {}),
    });
    await page.close();
  }
  return results;
}

/* ---------- constraint checks (the difficulty levers) ----------------- *
 * Six kinds, all deterministic:
 *   odd_one_out     which sibling is visually distinguished, by index
 *   numeric_order   numbers pulled from a set, in a required order
 *   budget          a counted ceiling: DOM nodes, CSS rules or source bytes
 *   no_computed     no element resolves a CSS property to a banned value
 *   no_external     no subresource loaded from off the page
 *   source_absent   a regex that must not appear in the HTML source
 * The first two carry anti-default briefs ("highlight the cheapest tier",
 * "annual costs more"); the last three carry prohibitions.
 */

const STYLE_KEYS = ["backgroundColor", "borderTopColor", "borderTopWidth",
                    "boxShadow", "outlineStyle", "transform", "color"];

async function checkConstraint(page, source, c) {
  const stepErr = await runSteps(page, c.steps);
  if (stepErr) return { name: c.name, ok: false, why: stepErr };

  if (c.kind === "odd_one_out") {
    const r = await page.evaluate((sel, keys) => {
      const els = [...document.querySelectorAll(sel)];
      if (els.length < 3) return { err: `only ${els.length} elements match ${sel}` };
      const sigs = els.map(el => {
        const cs = getComputedStyle(el);
        return keys.map(k => cs[k]).join("|");
      });
      const freq = {};
      for (const s of sigs) freq[s] = (freq[s] || 0) + 1;
      const unique = sigs.map((s, i) => (freq[s] === 1 ? i : -1)).filter(i => i >= 0);
      return { unique, n: els.length };
    }, c.selector, STYLE_KEYS);
    if (r.err) return { name: c.name, ok: false, why: r.err };
    if (r.unique.length !== 1)
      return { name: c.name, ok: false,
               why: r.unique.length === 0 ? "no element is visually distinguished"
                                          : `${r.unique.length} elements are distinguished, wanted exactly 1` };
    const got = r.unique[0];
    const want = c.expectIndex < 0 ? r.n + c.expectIndex : c.expectIndex;
    return got === want
      ? { name: c.name, ok: true }
      : { name: c.name, ok: false, why: `element ${got} is highlighted, brief asked for ${want}` };
  }

  if (c.kind === "numeric_order") {
    const nums = await page.evaluate((sel) =>
      [...document.querySelectorAll(sel)].map(el => {
        const m = (el.innerText || el.textContent || "").replace(/,/g, "").match(/-?\d+(\.\d+)?/);
        return m ? Number(m[0]) : null;
      }), c.selector);
    if (nums.some(n => n === null) || nums.length < 2)
      return { name: c.name, ok: false, why: `could not read numbers from ${c.selector}: ${JSON.stringify(nums)}` };
    const ok = c.order === "desc"
      ? nums.every((n, i) => i === 0 || nums[i - 1] > n)
      : nums.every((n, i) => i === 0 || nums[i - 1] < n);
    return ok ? { name: c.name, ok: true }
              : { name: c.name, ok: false, why: `${JSON.stringify(nums)} is not ${c.order}` };
  }

  if (c.kind === "no_computed") {
    const hits = await page.evaluate((prop, banned) => {
      const out = [];
      for (const el of document.querySelectorAll("body *, body")) {
        const v = getComputedStyle(el)[prop];
        if (banned.includes(v)) out.push(el.tagName.toLowerCase() + (el.className ? "." + String(el.className).split(" ")[0] : ""));
      }
      return out.slice(0, 5);
    }, c.property, c.banned);
    return hits.length === 0
      ? { name: c.name, ok: true }
      : { name: c.name, ok: false, why: `${c.property} is ${c.banned.join("/")} on ${hits.join(", ")}` };
  }

  if (c.kind === "no_external") {
    const hits = await page.evaluate(() => {
      const bad = [];
      const off = (u) => u && !/^(data:|blob:|#|about:)/i.test(u) && !/^file:/i.test(new URL(u, location.href).protocol + "//");
      for (const el of document.querySelectorAll("script[src], link[href], img[src], iframe[src], source[src]")) {
        const raw = el.getAttribute("src") || el.getAttribute("href") || "";
        if (/^(https?:)?\/\//i.test(raw)) bad.push(el.tagName.toLowerCase() + " → " + raw.slice(0, 60));
      }
      return bad.slice(0, 5);
    });
    return hits.length === 0
      ? { name: c.name, ok: true }
      : { name: c.name, ok: false, why: `external resources: ${hits.join("; ")}` };
  }

  // A budget. This is what survives translating FrontierCode's scope discipline
  // to a task with no baseline: it grades restraint against a stated ceiling
  // rather than against a reference patch, because a page generated from a
  // brief has no "before" to be measured against. One metric per entry, so a
  // page that holds two of three limits scores two of three.
  //
  // The numbers are calibrated, not guessed: across eighteen pages from three
  // frontier models built with no budget stated, nodes ran 67-119, CSS rules
  // 39-61, and source 9475-16473 bytes. Exactly one of the eighteen met all
  // three limits at once - proof the combination is reachable, and that almost
  // nothing reaches it by accident.
  if (c.kind === "budget") {
    const m = await page.evaluate(() => {
      let rules = 0;
      for (const sh of document.styleSheets) { try { rules += sh.cssRules.length; } catch { /* cross-origin */ } }
      return { nodes: document.querySelectorAll("*").length, css_rules: rules };
    });
    const got = c.metric === "bytes" ? source.length : m[c.metric];
    if (got === undefined) return { name: c.name, ok: false, why: `unknown budget metric ${c.metric}` };
    return got > c.max
      ? { name: c.name, ok: false, why: `${got} ${c.metric} — the budget is ${c.max}` }
      : { name: c.name, ok: true };
  }

  if (c.kind === "source_absent") {
    const re = new RegExp(c.pattern, c.flags ?? "iu");
    const m = source.match(re);
    return m ? { name: c.name, ok: false, why: `source contains ${JSON.stringify(String(m[0]).slice(0, 40))}` }
             : { name: c.name, ok: true };
  }

  return { name: c.name, ok: false, why: `unknown constraint kind ${c.kind}` };
}

/** Diagnostics only: axe-core, plus the rects the gallery draws. */
async function checkA11y(page) {
  await page.evaluate(AXE_SOURCE);
  const res = await page.evaluate(async () => {
    const r = await window.axe.run(document, {
      runOnly: { type: "rule", values: ["color-contrast", "label", "button-name", "link-name", "image-alt", "region"] },
    });
    return r.violations.map(v => ({
      id: v.id,
      nodes: v.nodes.map(n => ({
        target: n.target.join(" "),
        summary: (n.failureSummary || "").split("\n").pop().trim().slice(0, 80),
      })),
    }));
  });
  const contrast = res.filter(v => v.id === "color-contrast");
  const naming = res.filter(v => v.id !== "color-contrast");
  return {
    contrast_violations: contrast.reduce((a, v) => a + v.nodes.length, 0),
    naming_violations: naming.reduce((a, v) => a + v.nodes.length, 0),
    detail: res,
  };
}

/** Bounding boxes for every violation, in page coordinates — the gallery overlay. */
async function collectRects(page, a11y, responsive) {
  const targets = [];
  for (const v of a11y.detail) for (const n of v.nodes)
    targets.push({ selector: n.target, kind: v.id === "color-contrast" ? "contrast" : "naming", label: v.id });
  const rects = await page.evaluate((ts) => ts.map(t => {
    const el = document.querySelector(t.selector);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { kind: t.kind, label: t.label,
             rect: { x: r.x + scrollX, y: r.y + scrollY, w: r.width, h: r.height } };
  }).filter(Boolean), targets);
  for (const c of responsive.culprits ?? [])
    rects.push({ kind: "responsive", label: `${c.over}px`, rect: c.rect });
  return rects;
}

/* ---------- main ------------------------------------------------------ */

/* ---------- capture -------------------------------------------------- */

/** Tiles, not one viewport crop and not one tall strip. A viewport crop hides
 *  everything below the fold. One tall strip gets downscaled until the type is
 *  unreadable. 1280x1600 tiles keep both the whole page and its legibility.
 *  Cap at 3: 4800px is taller than anything we have seen. */
async function captureTiles(page, outDir, prefix) {
  const pageH = await page.evaluate(() => document.documentElement.scrollHeight);
  const n = Math.min(3, Math.max(1, Math.ceil(pageH / 1600)));
  const names = [];
  for (let i = 0; i < n; i++) {
    await page.setViewport({ width: 1280, height: 1600 });
    const name = n === 1 ? `${prefix}.png` : `${prefix}_${i + 1}.png`;
    await page.screenshot({
      path: path.join(outDir, name),
      clip: { x: 0, y: i * 1600, width: 1280, height: Math.min(1600, pageH - i * 1600) },
    });
    names.push(name);
  }
  await page.setViewport(DESKTOP);
  return names;
}

const ADVANCE = /(^|\W)(next|continue|proceed|submit|apply|enrol|enroll|register|finish|done|start|begin)(\W|$)/i;
const RETREAT = /(^|\W)(back|previous|prev|cancel|close|reset|clear|skip|edit)(\W|$)/i;

/** Fill visible empty fields with plausible values, so a validated step will
 *  let go. Best effort — a field it cannot guess is left alone. Checkboxes are
 *  skipped on purpose: an opt-in is the user's choice, not the walker's. */
async function fillVisible(page) {
  return page.evaluate(() => {
    const seen = (el) => {
      const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
      return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none";
    };
    const fire = (el) => {
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    };
    const VALUE = {
      email: "alex@example.com", tel: "07700900000", number: "12", range: "12",
      date: "2026-10-01", time: "18:00", url: "https://example.com",
      password: "correct-horse-14", text: "Alex Morgan", search: "Alex Morgan",
    };
    let filled = 0;
    for (const el of document.querySelectorAll("input, textarea, select")) {
      if (el.disabled || el.readOnly || !seen(el)) continue;
      const t = (el.type || "text").toLowerCase();
      if (["hidden", "submit", "button", "reset", "image", "file", "checkbox"].includes(t)) continue;
      if (el.tagName === "SELECT") {
        if (el.selectedIndex > 0) continue;
        const opt = [...el.options].find((o, i) => i > 0 && !o.disabled && o.value !== "");
        if (opt) { el.value = opt.value; fire(el); filled++; }
      } else if (t === "radio") {
        const group = el.name
          ? [...document.querySelectorAll("input[type=radio]")].filter(r => r.name === el.name)
          : [el];
        if (group.some(r => r.checked)) continue;
        el.checked = true; fire(el); filled++;
      } else if (!el.value) {
        el.value = VALUE[t] ?? VALUE.text; fire(el); filled++;
      }
    }
    return filled;
  });
}

/** Walk a multi-step UI, capturing each state.
 *
 *  A form whose steps 2..n do not exist in the DOM until a click cannot be seen
 *  in any single screenshot: the capture shows two of eleven fields, and
 *  everything read from it is wrong about the page. Tiling does not help — those
 *  pages are exactly one viewport tall because there is genuinely nothing else
 *  there yet. The only fix is to drive it.
 *
 *  Open briefs cannot declare a click path (we do not know the selectors), so
 *  this is a heuristic: fill what is visible, press the control that reads like
 *  "next", capture if the page actually changed. Never fatal, and it reports
 *  what it pressed so a reader can see how far it got. */
async function walkStates(page, url, outDir, max = 3) {
  const states = [];
  const sig = () => page.evaluate(
    () => (document.body.innerText || "").replace(/\s+/g, " ").trim().slice(0, 4000));
  // A native submit navigates away and takes the next step with it.
  await page.evaluate(() => {
    for (const f of document.forms) f.addEventListener("submit", e => e.preventDefault());
  });
  let before = await sig();
  for (let n = 2; n <= max + 1; n++) {
    const filled = await fillVisible(page);
    const clicked = await page.evaluate((adv, ret) => {
      const A = new RegExp(adv, "i"), R = new RegExp(ret, "i");
      const seen = (el) => {
        const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
        return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none";
      };
      const cands = [...document.querySelectorAll(
        "button, [role=button], input[type=submit], input[type=button], a[href]")]
        .filter(el => seen(el) && !el.disabled)
        .map(el => ({ el, label: (el.innerText || el.value || el.getAttribute("aria-label") || "").trim() }))
        .filter(c => A.test(c.label) && !R.test(c.label));
      if (!cands.length) return null;
      const c = cands[cands.length - 1];        // the advance control sits last
      if (c.el.tagName === "A") {
        const href = c.el.getAttribute("href") || "";
        if (href && !href.startsWith("#")) return null;   // do not leave the page
      }
      c.el.click();
      return c.label.slice(0, 60);
    }, ADVANCE.source, RETREAT.source);
    if (!clicked) break;
    await new Promise(r => setTimeout(r, 250));
    if (page.url().split("#")[0] !== url.split("#")[0]) break;   // navigated away
    const after = await sig();
    if (after === before) break;                                 // the click did nothing
    before = after;
    states.push({ n, clicked, filled, shots: await captureTiles(page, outDir, `state_${n}`) });
  }
  return states;
}

async function main() {
  const [pagePath, specPath, outDir] = process.argv.slice(2);
  const spec = JSON.parse(await readFile(specPath, "utf8"));
  await mkdir(outDir, { recursive: true });
  const url = pathToFileURL(path.resolve(pagePath)).href;

  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: true,
    args: ["--no-sandbox", "--force-color-profile=srgb", "--hide-scrollbars"],
  });

  const result = { loaded: false, families: {}, rects: [], console_errors: [] };
  try {
    const page = await browser.newPage();
    await page.setViewport(DESKTOP);
    page.on("pageerror", e => result.console_errors.push(String(e).slice(0, 200)));
    await page.goto(url, { waitUntil: "load", timeout: 15000 });
    await new Promise(r => setTimeout(r, 150));
    result.loaded = true;

    // behaviour first: it mutates page state, so it runs before the passive checks
    const behaviour = [];
    for (const a of spec.behaviour ?? []) {
      await page.goto(url, { waitUntil: "load" });   // fresh state per assertion
      await new Promise(r => setTimeout(r, 100));
      behaviour.push(await checkBehaviour(page, a));
    }
    result.families.behaviour = behaviour;

    if ((spec.constraints ?? []).length) {
      const source = await readFile(pagePath, "utf8");
      const cons = [];
      for (const c of spec.constraints) {
        await page.goto(url, { waitUntil: "load" });
        await new Promise(r => setTimeout(r, 100));
        cons.push(await checkConstraint(page, source, c));
      }
      result.families.constraints = cons;
    }

    await page.goto(url, { waitUntil: "load" });
    result.families.responsive = await checkResponsive(page, spec.responsive);

    const variants = [...(spec.robustness ?? []),
                      ...(spec.robustness_gen ? generateVariants(spec.robustness_gen) : [])];
    if (variants.length)
      result.families.robustness = await checkRobustness(browser, url, variants);

    await page.goto(url, { waitUntil: "load" });
    await new Promise(r => setTimeout(r, 120));
    result.families.a11y = await checkA11y(page);
    result.rects = await collectRects(page, result.families.a11y, result.families.responsive);

    result.screens = [{ n: 1, shots: await captureTiles(page, outDir, "render") }];
    try {
      for (const st of await walkStates(page, url, outDir)) result.screens.push(st);
    } catch (e) {
      result.walk_error = String(e).slice(0, 200);
    }
    await writeFile(path.join(outDir, "rects.json"), JSON.stringify(result.rects, null, 2));
  } catch (e) {
    result.error = String(e).slice(0, 300);
  } finally {
    await browser.close();
  }
  process.stdout.write(JSON.stringify(result));
}

main();
