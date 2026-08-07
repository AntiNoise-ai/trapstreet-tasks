"""One sweep for everything that has gone wrong before.

Each check exists because a real defect got through: a gold that leaked into
its own question, a case labelled as needing the image half that a text-only
pipeline answered, a judge that rejected a correct answer in a phrasing nobody
predicted.
"""
import json, os, re, subprocess, sys, tempfile, pathlib
TASK = pathlib.Path("."); F = TASK/"tests"/"fixtures"
CASES = json.loads((TASK/"gold.cases.json").read_text())["cases"]

def J(cid, a):
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        (td/"stdout.txt").write_text(a); (td/"meta.json").write_text('{"exit_code":0,"duration":1}')
        m = {"inputs_dir":str(TASK/"inputs"/cid),"expected_dir":str(TASK/"expected"/cid),
             "outputs_dir":str(td),"run":{"stdout":str(td/"stdout.txt"),
             "stderr":str(td/"stdout.txt"),"meta":str(td/"meta.json")}}
        r = json.loads(subprocess.run([sys.executable,"judge.py"],capture_output=True,text=True,
            env={**os.environ,"TRAPTASK_MANIFEST":json.dumps(m)}).stdout)
        return r["score"], [x["reason"] for x in r["matcher_results"] if not x["pass"]]

def variants(c):
    """Ways a correct answer legitimately gets written. Every shape here has
    appeared in a real run at some point today."""
    v = c["matchers"][0]["value"]; pct = c["matchers"][0].get("accept_percent_forms")
    names = [m["pattern"] for m in c["matchers"] if m["kind"]=="regex_required"]
    WORDS = {"treasury|tga|general account": "the U.S. Treasury, General Account",
             "atlanta": "Atlanta", "chicago": "Chicago",
             "new\\s*york": "New York", "richmond": "Richmond",
             "\\bface\\b": "face value", "\\bcash\\b": "cash value"}
    # every required phrase has to appear, and a real answer naming a district
    # or a valuation basis says it in every phrasing — the generator must too
    tag = ", ".join(WORDS.get(p, p) for p in names)
    tag = (tag + ", ") if tag else ""
    n = f"{v:,.2f}".rstrip("0").rstrip(".") if abs(v) < 1000 else f"{v:,.0f}"
    out = [
      f"{tag}{n}",                                                   # bare
      f"**{tag}{n}**\n\nThat figure comes straight from the table.",  # answer first
      f"Working through it ({tag}the two inputs are 1,234,567 and 89,012), "
      f"dividing gives {n}.",                                        # answer last
      f"On Wednesday, Jul 29, 2026 the answer is {tag}{n} — see table 6, page 9.",  # dates around it
      "## Calculation\n" + "\n".join(f"Step {i}: {1000*i:,} - {7*i} = {1000*i-7*i:,}" for i in range(1,7))
        + f"\n\n**Result: {tag}{n}**",                               # worked, many figures
    ]
    if pct:
        out.append(f"{tag}{v/100:.6g} as a fraction")                # fraction form
    return out

print("① 金标是否泄漏进题面")
bad = 0
for c in CASES:
    q = re.sub(r"\s+"," ",c["question"]).lower()
    val = abs(c["matchers"][0]["value"])
    for form in {f"{val:,.0f}", f"{val:.0f}", f"{val:.2f}"}:
        if len(form) >= 3 and form.lower() in q:
            print(f"   ⚠ {c['id']}: {form} 出现在题面"); bad += 1
print("   无" if not bad else "")

print("\n② scan / both 的金标能否从文本层拿到")
bad = 0
for c in CASES:
    if c["_layer"] == "text": continue
    f = F/f"pdf-inspector__{c['id']}.txt"
    if not f.exists(): continue
    said = f.read_text(); val = abs(c["matchers"][0]["value"])
    for form in ({f"{val:,.0f}", f"{val:.0f}"} if val >= 1000 else {f"{val:.2f}", f"{val:.1f}"}):
        if form in said:
            print(f"   ⚠ {c['id']} ({c['_layer']}): {form} 出现在纯文本层答案里"); bad += 1
print("   无 — 图片侧确实不可达" if not bad else "")

print("\n③ judge 对多种正确措辞的接受度")
bad = 0
for c in CASES:
    for i, a in enumerate(variants(c)):
        s, why = J(c["id"], a)
        if s != 1:
            bad += 1
            print(f"   ✗ {c['id']} 变体{i}: {why[0][:88] if why else ''}")
            print(f"        {a[:80]!r}")
print("   全部接受" if not bad else f"   共 {bad} 处误判")
