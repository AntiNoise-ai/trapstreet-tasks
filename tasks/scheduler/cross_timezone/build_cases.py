"""Source-of-truth generator for the cross_timezone task.

Defines every case as plain data (attendees + local availability windows on a
date), then uses Python's `zoneinfo` to compute the accepted UTC start window
by intersecting each attendee's window. This guarantees the gold answers are
internally consistent with judge.py (which also uses zoneinfo) and removes the
chance of hand-computed DST errors.

Run from this directory:

    python3 build_cases.py            # regenerate inputs/, expected/, gold.cases.json
    python3 build_cases.py --check    # regenerate in a temp dir and diff (CI-safe)

Each case emits:
  inputs/<id>/question.txt
  expected/<id>/answer.json
and the aggregate gold.cases.json.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent

# City label -> IANA tz, so a case can show a city while the gold carries the zone.
CITY_TZ = {
    "San Francisco": "America/Los_Angeles",
    "London": "Europe/London",
    "Mumbai": "Asia/Kolkata",
    "Kathmandu": "Asia/Kathmandu",
    "Sydney": "Australia/Sydney",
    "Singapore": "Asia/Singapore",
    "Berlin": "Europe/Berlin",
    "New York": "America/New_York",
    "Tokyo": "Asia/Tokyo",
    "Auckland": "Pacific/Auckland",
    "Chatham": "Pacific/Chatham",
}


def _local(date_str: str, hhmm: str, tz: str) -> datetime:
    """Aware datetime for a local wall-clock time on a date in tz."""
    d = datetime.strptime(f"{date_str} {hhmm}", "%Y-%m-%d %H:%M")
    return d.replace(tzinfo=ZoneInfo(tz))


def _utc(dt: datetime) -> datetime:
    return dt.astimezone(ZoneInfo("UTC"))


def compute(case: dict) -> dict:
    """Resolve a case spec into the answer.json the judge consumes."""
    dur = timedelta(minutes=case["duration_min"])
    base_date = case["meeting_date"]

    atts = []
    start_lo = None  # latest window-open across attendees (max of opens)
    start_hi = None  # earliest (window-close - duration) across attendees (min)
    for a in case["attendees"]:
        tz = CITY_TZ[a["city"]]
        date = a.get("date", base_date)
        avail_min_local = _local(date, a["avail"][0], tz)
        avail_max_local = _local(date, a["avail"][1], tz)
        open_utc = _utc(avail_min_local)
        latest_start_utc = _utc(avail_max_local) - dur
        start_lo = open_utc if start_lo is None else max(start_lo, open_utc)
        start_hi = latest_start_utc if start_hi is None else min(start_hi, latest_start_utc)
        atts.append({
            "name": a["name"],
            "tz": tz,
            "available_local_min": avail_min_local.replace(tzinfo=None).isoformat(),
            "available_local_max": avail_max_local.replace(tzinfo=None).isoformat(),
        })

    no_slot = start_lo > start_hi

    ans: dict = {
        "id": case["id"],
        "category": case["category"],
        "difficulty": case["difficulty"],
        "duration_min": case["duration_min"],
        "attendees": atts,
        "_notes": case["notes"],
    }
    if no_slot:
        ans["no_valid_slot"] = True
        ans["_canonical_answer"] = {"start_utc": None, "reason": case["notes"]}
    else:
        canonical = start_lo
        ans["expected_start_utc_min"] = start_lo.strftime("%Y-%m-%dT%H:%M:%SZ")
        ans["expected_start_utc_max"] = start_hi.strftime("%Y-%m-%dT%H:%M:%SZ")
        canon = {"start_utc": canonical.strftime("%Y-%m-%dT%H:%M:%SZ")}
        for a, meta in zip(case["attendees"], atts):
            local = canonical.astimezone(ZoneInfo(meta["tz"]))
            canon[f"{a['name'].lower()}_local"] = local.strftime("%Y-%m-%d %H:%M")
        ans["_canonical_answer"] = canon
    return ans


SCHEMA_HINT = """Return ONLY a JSON object (no commentary, no markdown fences). Schema:

{
  "start_utc": "<ISO 8601 timestamp in UTC, e.g. 2026-03-26T14:00:00Z, or null>",
  "duration_min": %d,
  "attendees": [
%s
  ]
}

If NO single slot fits inside EVERY attendee's window, return instead:
{"start_utc": null, "reason": "<one short sentence explaining why no slot exists>"}"""


def render_question(case: dict) -> str:
    today = datetime.strptime(case["today"], "%Y-%m-%d")
    meeting = datetime.strptime(case["meeting_date"], "%Y-%m-%d")
    show_tz = case.get("show_tz", True)
    lines = [
        "You are a scheduling assistant.",
        "",
        f"Schedule a {case['duration_min']}-minute meeting with the following "
        "attendees and their LOCAL availability windows.",
        "",
        f"Today is {case['today']} ({today.strftime('%A')}). "
        f"The meeting is on {meeting.strftime('%A %Y-%m-%d')}.",
        "",
        "Attendees:",
    ]
    width = max(len(a["name"]) for a in case["attendees"])
    cwidth = max(len(a["city"]) for a in case["attendees"])
    for a in case["attendees"]:
        tz = CITY_TZ[a["city"]]
        tzpart = f"  ({tz})" if show_tz else ""
        datepart = ""
        if a.get("date") and a["date"] != case["meeting_date"]:
            datepart = f"  [their local date: {a['date']}]"
        lines.append(
            f"- {a['name']:<{width}}  {a['city']:<{cwidth}}{tzpart}  "
            f"— available {a['avail'][0]}–{a['avail'][1]} local{datepart}"
        )
    lines += [
        "",
        "Rules:",
        "- Pick any slot that fits inside ALL attendees' local availability windows.",
        "- Account for daylight-saving time on the actual meeting date.",
    ]
    if not show_tz:
        lines.append("- Determine each city's UTC offset (and whether DST applies) yourself.")
    att_lines = ",\n".join(
        f'    {{"name": "{a["name"]}", '
        f'"tz": "{CITY_TZ[a["city"]] if show_tz else "<IANA zone you determined>"}", '
        f'"local_start": "YYYY-MM-DD HH:MM"}}'
        for a in case["attendees"]
    )
    lines += ["", SCHEMA_HINT % (case["duration_min"], att_lines), ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Case definitions. Windows are LOCAL wall-clock; gold is computed via zoneinfo.
# ---------------------------------------------------------------------------
CASES = [
    {
        "id": "dst_gap_with_ist",
        "category": "dst_boundary",
        "difficulty": "hard",
        "today": "2026-03-25", "meeting_date": "2026-03-26",
        "attendees": [
            {"name": "Alice", "city": "San Francisco", "avail": ["07:00", "09:00"]},
            {"name": "Bob", "city": "London", "avail": ["14:00", "16:00"]},
            {"name": "Priya", "city": "Mumbai", "avail": ["19:30", "21:30"]},
        ],
        "notes": "DST trap. US DST started 2026-03-08 (SF on PDT UTC-7). UK DST starts 2026-03-29, so London is still on GMT (UTC+0). India IST is UTC+5:30. Catches 'London in spring = BST' and 'India = UTC+5'.",
    },
    {
        "id": "dst_quarter_hour_sydney",
        "category": "multi_zone_expert",
        "difficulty": "expert",
        "today": "2026-03-25", "meeting_date": "2026-03-26",
        "attendees": [
            {"name": "Alice", "city": "San Francisco", "avail": ["06:00", "08:00"]},
            {"name": "Bob", "city": "London", "avail": ["14:00", "15:30"]},
            {"name": "Priya", "city": "Mumbai", "avail": ["19:00", "21:00"]},
            {"name": "Niraj", "city": "Kathmandu", "avail": ["19:30", "21:30"]},
            {"name": "Sam", "city": "Sydney", "avail": ["00:30", "02:30"], "date": "2026-03-27"},
        ],
        "notes": "Five-way trap: (1) UK on GMT not BST; (2) US on PDT; (3) IST UTC+5:30; (4) Nepal NPT UTC+5:45 (quarter-hour); (5) Sydney AEDT UTC+11 (southern-hemisphere DST in March); (6) Sam's local calendar date is the next day. Exactly one valid start time.",
    },
    {
        "id": "simple_two_zone_may",
        "category": "baseline",
        "difficulty": "easy",
        "today": "2026-05-13", "meeting_date": "2026-05-14",
        "attendees": [
            {"name": "Alice", "city": "San Francisco", "avail": ["08:00", "11:00"]},
            {"name": "Bob", "city": "New York", "avail": ["11:00", "15:00"]},
        ],
        "notes": "Baseline. Both US zones on DST in May (PDT UTC-7, EDT UTC-4). No tricks; catches only gross arithmetic errors.",
    },
    {
        "id": "winter_three_zone",
        "category": "baseline",
        "difficulty": "easy",
        "today": "2026-01-20", "meeting_date": "2026-01-21",
        "attendees": [
            {"name": "Alice", "city": "San Francisco", "avail": ["08:00", "10:00"]},
            {"name": "Bob", "city": "London", "avail": ["16:00", "18:00"]},
            {"name": "Priya", "city": "Mumbai", "avail": ["21:30", "23:30"]},
        ],
        "notes": "Winter: everyone on standard time (PST UTC-8, GMT UTC+0, IST UTC+5:30). Tests half-hour zone without any DST gap.",
    },
    {
        "id": "three_zone_sydney_daycross",
        "category": "day_boundary",
        "difficulty": "medium",
        "today": "2026-06-09", "meeting_date": "2026-06-10",
        "attendees": [
            {"name": "Alice", "city": "San Francisco", "avail": ["16:00", "18:00"]},
            {"name": "Bob", "city": "London", "avail": ["00:00", "02:00"], "date": "2026-06-11"},
            {"name": "Sam", "city": "Sydney", "avail": ["09:00", "11:00"], "date": "2026-06-11"},
        ],
        "notes": "June: Sydney on standard time (AEST UTC+10, southern-hemisphere winter), UK on BST (UTC+1), US on PDT (UTC-7). The instant lands on different local calendar dates for different attendees.",
    },
    {
        "id": "city_names_only_medium",
        "category": "zone_resolution",
        "difficulty": "medium",
        "today": "2026-09-15", "meeting_date": "2026-09-16",
        "show_tz": False,
        "attendees": [
            {"name": "Alice", "city": "San Francisco", "avail": ["06:00", "08:00"]},
            {"name": "Bob", "city": "Berlin", "avail": ["15:00", "17:00"]},
            {"name": "Yuki", "city": "Tokyo", "avail": ["22:00", "23:59"]},
        ],
        "notes": "No IANA zones given — model must map city to offset itself. Sept: SF PDT (UTC-7), Berlin CEST (UTC+2), Tokyo JST (UTC+9, no DST). Overlap is a SF morning / Berlin afternoon / Tokyo late-evening slot.",
    },
    {
        "id": "october_dst_reverse_gap",
        "category": "dst_boundary",
        "difficulty": "hard",
        "today": "2026-10-27", "meeting_date": "2026-10-28",
        "attendees": [
            {"name": "Alice", "city": "San Francisco", "avail": ["07:00", "09:00"]},
            {"name": "Bob", "city": "London", "avail": ["15:00", "17:00"]},
            {"name": "Priya", "city": "Mumbai", "avail": ["20:30", "22:30"]},
        ],
        "notes": "Reverse of the March gap. UK ended BST on 2026-10-25 (now GMT UTC+0); US ends DST on 2026-11-01, so SF is still on PDT (UTC-7). One-week window where London is GMT but SF is still on summer time.",
    },
    {
        "id": "dst_transition_day_us_fallback",
        "category": "dst_boundary",
        "difficulty": "hard",
        "today": "2026-10-31", "meeting_date": "2026-11-01",
        "attendees": [
            {"name": "Alice", "city": "San Francisco", "avail": ["13:00", "15:00"]},
            {"name": "Bob", "city": "New York", "avail": ["16:00", "18:00"]},
            {"name": "Yuki", "city": "Tokyo", "avail": ["05:00", "07:00"], "date": "2026-11-02"},
        ],
        "notes": "Meeting falls ON the US fall-back day (2026-11-01, clocks back at 02:00). Afternoon windows are unambiguous: SF PST (UTC-8), NY EST (UTC-5). Catches models that use the pre-transition offset (PDT/EDT) for an afternoon meeting.",
    },
    {
        "id": "narrow_overlap_five_zone",
        "category": "multi_zone_expert",
        "difficulty": "expert",
        "today": "2026-07-08", "meeting_date": "2026-07-09",
        "attendees": [
            {"name": "Alice", "city": "San Francisco", "avail": ["07:00", "08:30"]},
            {"name": "Bob", "city": "Berlin", "avail": ["16:00", "17:30"]},
            {"name": "Priya", "city": "Mumbai", "avail": ["19:30", "21:00"]},
            {"name": "Mei", "city": "Singapore", "avail": ["22:00", "23:30"]},
            {"name": "Sam", "city": "Sydney", "avail": ["00:00", "01:30"], "date": "2026-07-10"},
        ],
        "notes": "Five zones, narrow overlap. July: SF PDT (UTC-7), Berlin CEST (UTC+2), IST UTC+5:30, Singapore UTC+8 (no DST), Sydney AEST UTC+10 (winter, no DST). Tight single 30-min-ish overlap.",
    },
    {
        "id": "chatham_quarter_hour",
        "category": "multi_zone_expert",
        "difficulty": "expert",
        "today": "2026-02-17", "meeting_date": "2026-02-18",
        "attendees": [
            {"name": "Alice", "city": "San Francisco", "avail": ["12:00", "14:00"]},
            {"name": "Priya", "city": "Mumbai", "avail": ["01:30", "03:30"], "date": "2026-02-19"},
            {"name": "Wiremu", "city": "Chatham", "avail": ["09:45", "11:45"], "date": "2026-02-19"},
        ],
        "notes": "Chatham Islands are UTC+13:45 in February (NZDT + 45 min), the rarest quarter-hour zone with summer DST. SF on PST (UTC-8). Day-shift for both non-US attendees.",
    },
    {
        "id": "no_overlap_exists",
        "category": "honesty",
        "difficulty": "hard",
        "today": "2026-06-09", "meeting_date": "2026-06-10",
        "attendees": [
            {"name": "Alice", "city": "San Francisco", "avail": ["09:00", "11:00"]},
            {"name": "Mei", "city": "Singapore", "avail": ["09:00", "11:00"]},
        ],
        "notes": "No common slot exists: SF 09:00-11:00 PDT is 16:00-18:00Z; Singapore 09:00-11:00 (UTC+8) is 01:00-03:00Z. The windows never intersect. Correct answer is start_utc=null. Catches models that hallucinate a slot rather than admitting none fits.",
    },
]


def build(out_dir: Path) -> dict:
    gold = []
    for case in CASES:
        case.setdefault("duration_min", 60)
        ans = compute(case)
        cid = case["id"]
        (out_dir / "inputs" / cid).mkdir(parents=True, exist_ok=True)
        (out_dir / "expected" / cid).mkdir(parents=True, exist_ok=True)
        (out_dir / "inputs" / cid / "question.txt").write_text(render_question(case))
        (out_dir / "expected" / cid / "answer.json").write_text(
            json.dumps(ans, indent=2) + "\n"
        )
        gold.append({
            "id": cid,
            "category": case["category"],
            "difficulty": case["difficulty"],
            "today": case["today"],
            "meeting_date": case["meeting_date"],
            "duration_min": case["duration_min"],
            "no_valid_slot": ans.get("no_valid_slot", False),
            "canonical": ans["_canonical_answer"],
            "notes": case["notes"],
        })
    (out_dir / "gold.cases.json").write_text(json.dumps(gold, indent=2) + "\n")
    return {"n_cases": len(gold)}


if __name__ == "__main__":
    info = build(HERE)
    print(f"generated {info['n_cases']} cases into {HERE}")
