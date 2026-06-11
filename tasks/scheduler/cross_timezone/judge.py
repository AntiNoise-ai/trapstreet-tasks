"""Per-case judge for the cross_timezone scheduler task.

Reads the agent's stdout (must be a JSON object) and runs strict checks:

  1. stdout parses as JSON object
  2. start_utc is ISO 8601 with explicit UTC tz (Z or +00:00)
  3. start_utc lies inside expected_start_utc_min..expected_start_utc_max
  4. duration_min == expected duration
  5. For every gold attendee, the agent's reported local_start matches
     (start_utc converted to that attendee's IANA TZ via zoneinfo) ± 1 min
  6. For every gold attendee, the resulting local meeting (start + duration)
     fits inside their stated availability window

If any check fails → score 0.0. All checks pass → score 1.0. No partial credit.

Outputs JSON metrics to stdout; trap stores it as CaseResult.metrics.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _parse_iso(s: str) -> datetime | None:
    """Parse ISO 8601 string. Accepts trailing 'Z' or '+00:00'. Returns None on failure."""
    if not isinstance(s, str):
        return None
    s2 = s.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s2)
    except ValueError:
        return None


def _parse_local(s: str) -> datetime | None:
    """Parse a local datetime in 'YYYY-MM-DD HH:MM' or ISO form. Naive (no tz)."""
    if not isinstance(s, str):
        return None
    s2 = s.strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s2, fmt)
        except ValueError:
            continue
    return None


def _parse_agent_output(stdout: str) -> dict | tuple[None, str]:
    stdout = stdout.strip()
    # Strip common markdown code-fence wrappers (some models can't help themselves)
    if stdout.startswith("```"):
        lines = stdout.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stdout = "\n".join(lines).strip()
    try:
        obj = json.loads(stdout)
    except json.JSONDecodeError as e:
        return None, f"stdout is not valid JSON: {e}"
    if not isinstance(obj, dict):
        return None, "top-level output must be a JSON object"
    return obj


def judge_case(agent_stdout: str, expected: dict) -> dict[str, Any]:
    """Run all checks. Returns metrics dict including per-check pass/reason."""
    checks: list[dict] = []
    score = 1.0

    def fail(name: str, reason: str) -> None:
        nonlocal score
        checks.append({"check": name, "pass": False, "reason": reason})
        score = 0.0

    def ok(name: str, reason: str = "ok") -> None:
        checks.append({"check": name, "pass": True, "reason": reason})

    # 1. JSON parse
    parsed = _parse_agent_output(agent_stdout)
    if isinstance(parsed, tuple):
        fail("json_parse", parsed[1])
        return {"score": 0.0, "matcher_results": checks}
    ans = parsed
    ok("json_parse")

    # 1b. Honesty cases: gold says no slot fits everyone. The only correct
    # answer is start_utc == null (a refusal). Any proposed time = hallucination.
    if expected.get("no_valid_slot"):
        if "start_utc" not in ans:
            fail("no_slot_refusal", "expected start_utc: null, but field missing entirely")
        elif ans.get("start_utc") is None:
            ok("no_slot_refusal", "correctly returned start_utc: null")
        else:
            fail(
                "no_slot_refusal",
                f"no slot fits all windows, but model proposed start_utc={ans.get('start_utc')!r}",
            )
        final = 0.0 if any(not c["pass"] for c in checks) else 1.0
        return {
            "score": final,
            "matcher_results": checks,
            "agent_start_utc": ans.get("start_utc"),
            "gold_canonical_utc": None,
            "id": expected.get("id"),
            "category": expected.get("category"),
            "difficulty": expected.get("difficulty"),
        }

    # 2. start_utc field present + parseable + has tzinfo
    start_utc_str = ans.get("start_utc")
    if not start_utc_str:
        fail("start_utc_present", "field missing")
        return {"score": 0.0, "matcher_results": checks}
    dt = _parse_iso(start_utc_str)
    if dt is None or dt.tzinfo is None:
        fail("start_utc_iso8601_utc", f"could not parse {start_utc_str!r} as ISO 8601 with explicit UTC offset")
        return {"score": 0.0, "matcher_results": checks}
    dt_utc = dt.astimezone(timezone.utc)
    ok("start_utc_iso8601_utc", f"parsed as {dt_utc.isoformat()}")

    # 3. start_utc in accepted window
    exp_min = _parse_iso(expected["expected_start_utc_min"])
    exp_max = _parse_iso(expected["expected_start_utc_max"])
    if exp_min is None or exp_max is None:
        fail("gold_window", "gold answer.json has malformed expected_start_utc_min/max")
        return {"score": 0.0, "matcher_results": checks}
    if not (exp_min <= dt_utc <= exp_max):
        fail(
            "start_utc_in_window",
            f"start_utc {dt_utc.isoformat()} is outside accepted [{exp_min.isoformat()}, {exp_max.isoformat()}]",
        )
    else:
        ok("start_utc_in_window")

    # 4. duration matches
    exp_dur = int(expected["duration_min"])
    got_dur = ans.get("duration_min")
    if got_dur != exp_dur:
        fail("duration_min", f"got {got_dur!r}, expected {exp_dur}")
    else:
        ok("duration_min")

    duration = timedelta(minutes=exp_dur)

    # 5 + 6. Per-attendee checks
    model_atts = ans.get("attendees") or []
    if not isinstance(model_atts, list):
        fail("attendees_list", "attendees must be a list")
        return {"score": score, "matcher_results": checks}

    model_by_name = {str(a.get("name", "")).strip().lower(): a for a in model_atts if isinstance(a, dict)}

    for gold_att in expected["attendees"]:
        name = gold_att["name"]
        tz_name = gold_att["tz"]
        try:
            tz = ZoneInfo(tz_name)
        except ZoneInfoNotFoundError:
            fail(f"attendee_{name}_gold_tz", f"gold TZ {tz_name!r} not in zoneinfo database")
            continue
        local_dt = dt_utc.astimezone(tz)

        # Availability window check (gold-side, authoritative)
        avail_min = _parse_local(gold_att["available_local_min"])
        avail_max = _parse_local(gold_att["available_local_max"])
        if avail_min is None or avail_max is None:
            fail(f"attendee_{name}_gold_window", "malformed gold availability")
            continue
        local_naive = local_dt.replace(tzinfo=None)
        latest_start = avail_max - duration
        if not (avail_min <= local_naive <= latest_start):
            fail(
                f"attendee_{name}_availability",
                f"start={local_naive.isoformat()} not in [{avail_min.isoformat()}, {latest_start.isoformat()}]",
            )
        else:
            ok(f"attendee_{name}_availability", f"local {local_naive.isoformat()} fits window")

        # Model's reported local_start matches our computed
        model_att = model_by_name.get(name.lower())
        if model_att is None:
            fail(f"attendee_{name}_in_output", "missing from agent output")
            continue
        reported = _parse_local(str(model_att.get("local_start", "")))
        if reported is None:
            fail(
                f"attendee_{name}_local_format",
                f"local_start {model_att.get('local_start')!r} not parseable as YYYY-MM-DD HH:MM",
            )
            continue
        diff_min = abs((local_naive - reported).total_seconds()) / 60.0
        if diff_min > 1.0:
            fail(
                f"attendee_{name}_local_match",
                f"reported {reported.isoformat()} vs computed {local_naive.isoformat()} (diff {diff_min:.1f} min)",
            )
        else:
            ok(f"attendee_{name}_local_match", f"reported {reported.isoformat()} ≈ computed (Δ {diff_min:.1f} min)")

    # Recompute score from checks (in case any later fail overrode the early return path)
    final_score = 0.0 if any(not c["pass"] for c in checks) else 1.0
    return {
        "score": final_score,
        "matcher_results": checks,
        "agent_start_utc": ans.get("start_utc"),
        "gold_canonical_utc": expected.get("_canonical_answer", {}).get("start_utc"),
        "id": expected.get("id"),
        "category": expected.get("category"),
        "difficulty": expected.get("difficulty"),
    }


def main() -> None:
    payload = json.loads(os.environ["TRAPTASK_PAYLOAD"])

    stdout = Path(payload["outputs"]["case_stdout"]).read_text()
    exit_code = json.loads(Path(payload["outputs"]["case_meta.json"]).read_text())["exit_code"]
    expected = json.loads(Path(payload["expected"]["answer.json"]).read_text())

    # Pick up usage.json if the solution captured it (token + cost tracking)
    usage_record: dict[str, Any] = {}
    usage_path = payload["outputs"].get("usage.json")
    if usage_path and Path(usage_path).exists():
        try:
            usage_record = json.loads(Path(usage_path).read_text())
        except json.JSONDecodeError:
            pass

    if exit_code != 0:
        out = {
            "score": 0.0,
            "reason": f"solution exited {exit_code}",
            "agent_answer": stdout.strip()[:500],
            "id": expected.get("id"),
            "category": expected.get("category"),
            "difficulty": expected.get("difficulty"),
            **usage_record,
        }
        print(json.dumps(out))
        return

    metrics = judge_case(stdout, expected)
    metrics["agent_answer"] = stdout.strip()[:500]
    metrics.update(usage_record)
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
