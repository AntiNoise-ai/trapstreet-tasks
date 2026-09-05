"""An optional judge panel — one model, three lenses.

Diagnostic tier only. Nothing here ever moves `score`; see judge.py for why.

What it is for
--------------
The deterministic checks own `adherence` and half of `tech`. They structurally
cannot reach `structure` (did it make the right moves) or `execution` (is the
craft there). That gap is the whole reason this file exists: not that a judge
separates better, but that it reaches where the instrument cannot.

`tech` and `adherence` are kept anyway even though they overlap the checks —
they are a free partial oracle. A judge that scores adherence 3 on a page that
failed three constraint checks has disqualified itself, at no labelling cost.

Scale, axis split and the anchoring rule: see docs/writing-a-judge-rubric.md.
The 1-3 forced choice replaces an earlier 0-10 copied from Startrise; wide
scales cluster in the middle (inter-rater reliability 0.45-0.60 on 1-5), and
the tell was that the 0-10 version needed an anchor sentence to fight it.

Anchors
-------
`check/anchors/` holds seven screenshots the task owner sorted blind, placed
directly on the 1-3 scale: three she would ship, two she judged fine but would
not ship, and two she called clearly worse than either. Spread across the open
briefs and, at every level, across different labs — anchored to one lab's
"good", a judge learns that lab's style rather than quality.

The bottom two arrived late and only because she overruled me. I had looked at
them and read them as spare and on-brief; she saw the gap immediately. That is
the argument for anchors in one line: the rubric carries my words, the anchors
carry her eye, and where they disagree hers is the one that counts.

They are the 80%. The rubric text above is the 20%.

Two honest limits. The sort was overall, not per-axis, so the anchors calibrate
the general bar and not each axis independently. And they only reach the lenses
that see a rendering — the source-reading lens gets no anchors, because we have
no source-level labels and five full documents would swamp its context.

Why one model and not three labs
--------------------------------
Startrise's own 839-call bias audit found that nine judges spanning seven model
families are worth "only about 2 independent votes". Vendor diversity buys
self-preference protection we cannot guarantee anyway — we do not control which
model an arm runs. What it costs is two extra API keys from every submitter,
against a platform whose pitch is that a leaderboard row takes ten minutes. So:
one key, the one they already needed to run the arm, and three lenses. The
perspective diversity lives in the prompts.

Which model
-----------
Sonnet 5, not Opus. Three reasons, in order of weight:

* The bias audit's disqualifying profile is "weak and lenient" — Haiku 4.5 was
  simultaneously the worst builder, the most lenient judge (+6.92) and the most
  self-favouring (+7.04). Sonnet 5 sits at the other end: it scored its own work
  **below** what the panel gave it (-1.39), the best self-preference profile in
  that audit.
* A serious arm is most likely to be an Opus-tier model. Judging with Opus
  maximises the arm-equals-judge collision; judging with Sonnet moves it to a
  less-populated cell. A single judge cannot eliminate it, only relocate it.
* It is 2.5x cheaper ($2/$10 per MTok against $5/$25), and this cost lands on
  the submitter, once per case, forever.

Caveat worth keeping visible: that -1.39 is one lab's audit of one setup. It is
evidence, not a law.

Opt-in: does nothing unless TRAP_PANEL=1 and a key is present. A submission
without it is still a complete, valid run. Note the "one key they already have"
argument only holds when the arm is itself an Anthropic model — an arm running
GPT or Gemini needs a new key purely for this panel. That is the strongest
reason to keep it diagnostic and optional rather than part of the score.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path

MODEL = os.environ.get("TRAP_PANEL_MODEL", "claude-sonnet-5")
EFFORT = os.environ.get("TRAP_PANEL_EFFORT", "medium")

AXES = ("structure", "execution", "tech", "adherence")

RUBRIC = """You are scoring one self-contained HTML page a developer produced from a brief.

Score four axes. Each is 1, 2, or 3. Nothing else.

  1 = broken      2 = fine      3 = actually good

Force the choice. "Fine" is the honest answer for most work. If you find
yourself giving 3s freely, you have stopped reading.

  structure   — did it make the right moves for THIS brief? Is there one clear
                thing being said, or five? Is the thing that matters most the
                thing you see first? Was anything left out that should not
                have been?
  execution   — is the craft there? Spacing on a scale, type with a real
                hierarchy, things aligned, restraint. Considered, or assembled?
  tech        — is the markup sound, the CSS coherent, the JavaScript
                defensive? Would you be willing to change this next month?
  adherence   — did it do what was asked, in full, without inventing a
                different task?

Score what is in front of you. You do not know who or what produced it, and
speculating about that is out of scope."""

LENSES = {
    "craft": (
        "You are a design director. You are looking at the rendered page and the "
        "brief it was built from. You care about how it reads at a glance and "
        "whether the details hold up.",
        ("screenshot", "brief"),
    ),
    "engineering": (
        "You are a graphics engineer reading the source. You have not seen it "
        "rendered. You care about whether the implementation is sound and what it "
        "would be like to change.",
        ("source", "brief"),
    ),
    "brief": (
        "You are the client who wrote this brief. You are checking whether you got "
        "what you asked for. You are not impressed by effort spent elsewhere.",
        ("brief", "screenshot"),
    ),
}


def _schema() -> dict:
    return {
        "type": "object",
        "properties": {
            # enum, not minimum/maximum — structured outputs rejects numeric
            # bounds on integers (400). This is the better spelling anyway: it
            # makes the three-point scale a closed set rather than a range.
            **{a: {"type": "integer", "enum": [1, 2, 3]} for a in AXES},
            "note": {"type": "string", "description": "One sentence, the single most decisive observation."},
        },
        "required": [*AXES, "note"],
        "additionalProperties": False,
    }


ANCHOR_DIR = Path(__file__).resolve().parent / "anchors"

ANCHOR_PREAMBLE = (
    "Before you score anything, calibrate. The person who commissioned these "
    "briefs was shown submissions with the authors hidden and placed them on "
    "the same 1-3 scale you are about to use. Here is where she put them. "
    "Match this bar — not your own."
)

LEVEL_LABEL = {3: "3 — actually good, she would ship this",
               2: "2 — fine, but she would not ship it",
               1: "1 — clearly worse than the above"}


def _img(path: Path) -> dict:
    media = "image/jpeg" if path.suffix in (".jpg", ".jpeg") else "image/png"
    return {"type": "image",
            "source": {"type": "base64", "media_type": media,
                       "data": base64.standard_b64encode(path.read_bytes()).decode()}}


def _anchor_blocks() -> list[dict]:
    manifest = ANCHOR_DIR / "anchors.json"
    if not manifest.exists():
        return []
    blocks = [{"type": "text", "text": ANCHOR_PREAMBLE}]
    for a in sorted(json.loads(manifest.read_text()), key=lambda a: -a["level"]):
        f = ANCHOR_DIR / a["file"]
        if not f.exists():
            continue
        blocks.append(_img(f))
        blocks.append({"type": "text",
                       "text": f"{a['kind']} — {LEVEL_LABEL[a['level']]}"})
    blocks.append({"type": "text",
                   "text": "End of calibration. Now the page you are scoring."})
    return blocks


def _content(parts: tuple[str, ...], brief: str, source: str, shots: list[Path]) -> list[dict]:
    blocks: list[dict] = []
    if "screenshot" in parts:
        blocks += _anchor_blocks()
    for part in parts:
        if part == "screenshot" and shots:
            for i, sh in enumerate(shots):
                blocks.append(_img(sh))
                where = "the page" if len(shots) == 1 else f"part {i+1} of {len(shots)}, top to bottom"
                blocks.append({"type": "text",
                               "text": f"Above: {where}, rendered 1280px wide."})
            blocks.append({"type": "text", "text":
                "Note: this is the page as it first loads. Anything that only appears "
                "after a click is not visible here — do not penalise its absence, and "
                "do not assume it is missing."})
        elif part == "brief":
            blocks.append({"type": "text", "text": f"The brief it was built from:\n\n{brief}"})
        elif part == "source":
            blocks.append({"type": "text", "text": f"The source:\n\n{source[:120_000]}"})
    blocks.append({"type": "text", "text": "Score it."})
    return blocks


def run_panel(brief: str, source: str, screenshots: list[Path] | Path | None) -> dict:
    """Return {status, axes: {axis: median}, lenses: {...}} — never raises."""
    if os.environ.get("TRAP_PANEL") != "1":
        return {"status": "not_requested"}
    if screenshots is None:
        screenshots = []
    elif isinstance(screenshots, Path):
        screenshots = [screenshots]
    screenshots = [s for s in screenshots if s.exists()]
    try:
        import anthropic
    except ImportError:
        return {"status": "skipped", "why": "anthropic sdk not installed"}

    try:
        client = anthropic.Anthropic(max_retries=5)
    except Exception as e:                                  # no credentials configured
        return {"status": "skipped", "why": f"no client: {str(e)[:120]}"}

    lenses: dict[str, dict] = {}
    for name, (stance, parts) in LENSES.items():
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=8000,
                system=f"{stance}\n\n{RUBRIC}",
                output_config={"format": {"type": "json_schema", "schema": _schema()},
                               "effort": EFFORT},
                messages=[{"role": "user", "content": _content(parts, brief, source, screenshots)}],
            )
            text = next((b.text for b in resp.content if b.type == "text"), "")
            lenses[name] = json.loads(text)
        except Exception as e:
            lenses[name] = {"error": f"{type(e).__name__}: {str(e)[:160]}"}

    scored = [v for v in lenses.values() if "error" not in v]
    if not scored:
        return {"status": "failed", "lenses": lenses}

    def median(xs: list[int]) -> float:
        xs = sorted(xs)
        n = len(xs)
        return float(xs[n // 2]) if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2

    axes = {a: median([v[a] for v in scored if a in v]) for a in AXES}
    # Spread is kept on purpose: a wide spread across lenses is the signal that
    # this page is contentious, which is worth more than the median alone.
    spread = {a: max(v[a] for v in scored if a in v) - min(v[a] for v in scored if a in v)
              for a in AXES}
    return {
        "status": "ok",
        "model": MODEL,
        "effort": EFFORT,
        "n_lenses": len(scored),
        "axes": axes,
        "spread": spread,
        "lenses": lenses,
    }


if __name__ == "__main__":
    import sys
    page = Path(sys.argv[1])
    brief_p = Path(sys.argv[2])
    shots = [Path(a) for a in sys.argv[3:]]
    print(json.dumps(run_panel(brief_p.read_text(), page.read_text(), shots), indent=2))
