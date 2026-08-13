# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "anthropic",
#     "openai",
# ]
# ///
"""Calibration harness -- runs a subset of cells against one model and scores
them with this task's own judge.

This exists because the instrument's validity depends on two numbers that must
be established BEFORE the full matrix is run:

  1. **The fairness gate.** The strongest available model at high effort must
     score 1.0 on every adversarial case at N=6. A case it misses with only
     six tools in front of it is unfair, not hard, and gets rewritten. Without
     this, a later "degradation" could just be cases nobody could solve.

  2. **The difficulty band.** A mid-tier model should land roughly in 40-90%
     on adversarial N=6. At the ceiling, the near-miss families are not
     discriminating and no amount of filler will rescue them -- that is
     exactly the failure that made this task's predecessor come back flat
     across 270 scores. At the floor, they are probably unfair.

`tp run` has no case filter, so this talks to the providers directly rather
than running all 64 cases to look at 8 of them.

    python3 calibrate.py --estimate --cells adv_n6_mid          # no API calls
    python3 calibrate.py --provider anthropic --model claude-opus-5 \\
        --effort high --cells adv_n6_mid
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from judge import score_case  # noqa: E402

HERE = Path(__file__).resolve().parent
FENCE_RE = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)
QUERY_RE = re.compile(r"# User request\s*\n\n(.*?)\n\n# Your task", re.DOTALL)

# Published per-million-token prices, input/output, for the estimate mode only.
PRICES = {
    "claude-opus-5": (5.0, 25.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "meta-llama/llama-3.1-8b-instruct": (0.02, 0.03),
    "qwen/qwen-2.5-7b-instruct": (0.04, 0.10),
}


def load_cases(cells: list[str]) -> list[dict]:
    grid = json.loads((HERE / "gold.cases.json").read_text())["cases"]
    return [c for c in grid if c["category"] in cells]


def read_case(case: dict) -> tuple[list[dict], str, dict]:
    prompt = (HERE / "inputs" / case["id"] / "prompt.txt").read_text()
    tools = json.loads(FENCE_RE.search(prompt).group(1))
    query = QUERY_RE.search(prompt).group(1).strip()
    expected = json.loads((HERE / "expected" / case["id"] / "answer.json").read_text())
    return tools, query, expected


def call_anthropic(model: str, effort: str, tools_raw: list[dict], query: str) -> tuple[str, dict]:
    from anthropic import Anthropic

    client = Anthropic(max_retries=10)
    tools = [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]}
             for t in tools_raw]
    kwargs: dict = {"max_tokens": 8192}
    if any(model.startswith(f"claude-{f}-5") for f in ("opus", "sonnet", "fable")):
        kwargs["thinking"] = {"type": "adaptive"}
        kwargs["output_config"] = {"effort": effort}

    msg = client.messages.create(
        model=model, tools=tools, tool_choice={"type": "any"},
        messages=[{"role": "user", "content": query}], **kwargs,
    )
    # Real usage, not a chars/4 guess -- this is what stage-3 costs get repriced
    # from, and dense JSON tokenizes well below 4 chars/token.
    usage = {"input_tokens": getattr(msg.usage, "input_tokens", None),
             "output_tokens": getattr(msg.usage, "output_tokens", None)}
    uses = [b for b in msg.content if b.type == "tool_use"]
    if not uses:
        return "", usage
    return json.dumps({"name": uses[0].name, "arguments": uses[0].input}), usage


def call_openrouter(model: str, tools_raw: list[dict], query: str) -> tuple[str, dict]:
    from openai import OpenAI

    client = OpenAI(base_url="https://openrouter.ai/api/v1",
                    api_key=os.environ["OPENROUTER_API_KEY"], max_retries=5)
    tools = [{"type": "function", "function": {
        "name": t["name"], "description": t["description"], "parameters": t["parameters"]}}
        for t in tools_raw]

    def request(choice: str):
        return client.chat.completions.create(
            model=model, tools=tools, tool_choice=choice, max_tokens=2048,
            messages=[{"role": "user", "content": query}])

    try:
        resp = request("required")
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] tool_choice=required failed ({exc}); retrying auto", file=sys.stderr)
        resp = request("auto")

    u = getattr(resp, "usage", None)
    usage = {"input_tokens": getattr(u, "prompt_tokens", None),
             "output_tokens": getattr(u, "completion_tokens", None)}
    calls = getattr(resp.choices[0].message, "tool_calls", None)
    if not calls:
        return "", usage
    fn = calls[0].function
    try:
        arguments = json.loads(fn.arguments) if isinstance(fn.arguments, str) else fn.arguments
    except (json.JSONDecodeError, TypeError):
        arguments = {}
    return json.dumps({"name": fn.name, "arguments": arguments}), usage


def estimate(cases: list[dict], model: str) -> None:
    """Report the size of the job without spending anything."""
    total_chars = sum(len((HERE / "inputs" / c["id"] / "prompt.txt").read_text()) for c in cases)
    in_tok = total_chars / 4          # ~4 chars/token for dense JSON
    out_tok = len(cases) * 400        # tool call + any thinking, generous
    p_in, p_out = PRICES.get(model, (0.0, 0.0))
    cost = in_tok / 1e6 * p_in + out_tok / 1e6 * p_out
    print(f"cases:            {len(cases)}")
    print(f"input tokens:     ~{in_tok/1000:.1f}k")
    print(f"output tokens:    ~{out_tok/1000:.1f}k (assumed)")
    print(f"model:            {model}")
    if p_in:
        print(f"estimated cost:   ~${cost:.2f} for one pass")
    else:
        print("estimated cost:   unknown (model not in PRICES)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=["anthropic", "openrouter"])
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument("--effort", default="high", choices=["low", "medium", "high"])
    ap.add_argument("--cells", default="adv_n6_mid",
                    help="Comma-separated category values, e.g. adv_n6_mid,clean_n6_mid")
    ap.add_argument("--estimate", action="store_true", help="Size the job; make no API calls.")
    ap.add_argument("--out", default=None, help="Write per-case JSON results here.")
    args = ap.parse_args()

    cells = [c.strip() for c in args.cells.split(",") if c.strip()]
    cases = load_cases(cells)
    if not cases:
        print(f"no cases match cells {cells}", file=sys.stderr)
        return 1

    if args.estimate:
        estimate(cases, args.model)
        return 0

    if not args.provider:
        print("--provider is required unless --estimate is passed", file=sys.stderr)
        return 1

    def run_one(case: dict) -> dict:
        tools, query, expected = read_case(case)
        try:
            if args.provider == "anthropic":
                raw, usage = call_anthropic(args.model, args.effort, tools, query)
            else:
                raw, usage = call_openrouter(args.model, tools, query)
        except Exception as exc:  # noqa: BLE001
            return {**case, "score": 0.0, "failure_mode": "solution_error",
                    "error": str(exc)[:200], "usage": {}}
        metrics = score_case(raw, expected) if raw else {
            "score": 0.0, "reason": "no tool call emitted", "failure_mode": "unparseable"}
        return {**case, **metrics, "usage": usage}

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(run_one, cases))

    print(f"\n{args.model} (effort={args.effort}) on cells {cells}\n")
    print(f"  {'case':<9} {'intent':<28} {'score':>5}  {'failure':<16} called")
    print(f"  {'-'*9} {'-'*28} {'-'*5}  {'-'*16} {'-'*40}")
    for r in sorted(results, key=lambda x: x["id"]):
        called = r.get("called_tool") or r.get("error", "") or "-"
        print(f"  {r['id']:<9} {r['intent']:<28} {r['score']:>5.1f}  "
              f"{str(r.get('failure_mode') or '-'):<16} {called}")

    # Provider/transport failures are held OUT of the accuracy denominator.
    # A context-window overflow at N=300 is a hard limit, not a discrimination
    # failure, and folding it into accuracy would read as "the small model
    # degraded at scale" -- the one headline that must never be an artifact.
    errored = [r for r in results if r.get("failure_mode") == "solution_error"]
    valid = [r for r in results if r.get("failure_mode") != "solution_error"]
    acc = sum(r["score"] for r in valid) / len(valid) if valid else 0.0
    misses = [r for r in valid if r["score"] == 0.0]
    print(f"\n  accuracy: {acc:.3f}  ({len(valid) - len(misses)}/{len(valid)} scored cases)")
    if errored:
        print(f"  provider errors (EXCLUDED from accuracy): {len(errored)}")
        for r in errored:
            print(f"    {r['id']}: {r.get('error', '?')}")
    if misses:
        print("  missed:")
        for r in misses:
            print(f"    {r['id']} ({r['intent']}): {r.get('reason', r.get('error', '?'))}")

    tok = [r["usage"].get("input_tokens") for r in results if r.get("usage", {}).get("input_tokens")]
    if tok:
        per_case = sum(tok) / len(tok)
        chars = sum(len((HERE / "inputs" / r["id"] / "prompt.txt").read_text()) for r in results)
        print(f"\n  measured input tokens: {sum(tok)/1000:.1f}k total, "
              f"~{per_case/1000:.1f}k per case ({chars/sum(tok):.2f} chars/token)")

    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=2))
        print(f"\n  wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
