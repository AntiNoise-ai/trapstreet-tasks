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
async function checkRobustness(browser, url, variants) {
  const results = [];
  for (const v of variants) {
    const page = await browser.newPage();      // fresh page: no script build-up
    const errors = [];
    page.on("pageerror", e => errors.push(String(e).slice(0, 120)));
    await page.setViewport(v.viewport === "phone" ? PHONE : DESKTOP);
    await page.evaluateOnNewDocument((data) => {
      window.__DATA__ = data;
    }, v.data);
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
      if (v.expectTitle !== undefined && out.title !== v.expectTitle)
        fails.push(`document.title is now ${JSON.stringify(out.title)}`);
    }
    if (errors.length) fails.push(`threw: ${errors[0]}`);

    results.push({ name: v.name, ok: fails.length === 0, why: fails.length ? fails.join("; ") : null });
    await page.close();
  }
  return results;
}

/* ---------- constraint checks (the difficulty levers) ----------------- *
 * Five kinds, all deterministic:
 *   odd_one_out     which sibling is visually distinguished, by index
 *   numeric_order   numbers pulled from a set, in a required order
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

    if ((spec.robustness ?? []).length)
      result.families.robustness = await checkRobustness(browser, url, spec.robustness);

    await page.goto(url, { waitUntil: "load" });
    await new Promise(r => setTimeout(r, 120));
    result.families.a11y = await checkA11y(page);
    result.rects = await collectRects(page, result.families.a11y, result.families.responsive);

    // Tiles, not one viewport crop and not one tall strip. A viewport crop hides
    // everything below the fold — a multi-step form scored from its first step
    // is scored on two of eleven fields. One tall strip gets downscaled until
    // the type is unreadable. 1280x1600 tiles keep both the whole page and its
    // legibility. Cap at 3: 4800px is taller than anything we have seen.
    const pageH = await page.evaluate(() => document.documentElement.scrollHeight);
    const tiles = Math.min(3, Math.max(1, Math.ceil(pageH / 1600)));
    for (let i = 0; i < tiles; i++) {
      await page.setViewport({ width: 1280, height: 1600 });
      await page.screenshot({
        path: path.join(outDir, tiles === 1 ? "render.png" : `render_${i + 1}.png`),
        clip: { x: 0, y: i * 1600, width: 1280, height: Math.min(1600, pageH - i * 1600) },
      });
    }
    await page.setViewport(DESKTOP);
    await writeFile(path.join(outDir, "rects.json"), JSON.stringify(result.rects, null, 2));
  } catch (e) {
    result.error = String(e).slice(0, 300);
  } finally {
    await browser.close();
  }
  process.stdout.write(JSON.stringify(result));
}

main();
