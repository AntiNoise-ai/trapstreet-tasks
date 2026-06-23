"""Thin the-odds-api v4 client + pure parsers + team-code helpers.

Network is isolated to fetch_odds()/fetch_scores() (urllib, stdlib only). The
parse_* / key helpers are pure and unit-tested against captured fixture JSON.

API docs: https://the-odds-api.com/liveapi/guides/v4/
Sport key: soccer_fifa_world_cup ; market: h2h ; oddsFormat: decimal.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

SPORT = "soccer_fifa_world_cup"
_BASE = "https://api.the-odds-api.com/v4"

# Canonical FIFA-style 3-letter codes. Keyed by a normalized team name so both the
# web/Wikipedia spelling (used at seed time) and the-odds-api spelling (used at
# snapshot/grade time) resolve to the SAME code — that's what lets odds + results
# get joined back onto seeded cases. Add aliases as the bracket fills out.
_TEAM_CODES = {
    # 2026 group-stage teams referenced so far (extend freely)
    "switzerland": "SUI",
    "canada": "CAN",
    "bosnia and herzegovina": "BIH", "bosnia herzegovina": "BIH", "bosnia": "BIH",
    "qatar": "QAT",
    "scotland": "SCO",
    "panama": "PAN",
    "brazil": "BRA",
    "morocco": "MAR",
    "haiti": "HAI",
    "czechia": "CZE", "czech republic": "CZE",
    "mexico": "MEX",
    "south africa": "RSA",
    "south korea": "KOR", "korea republic": "KOR", "republic of korea": "KOR",
    "united states": "USA", "usa": "USA", "united states of america": "USA",
    "argentina": "ARG", "france": "FRA", "spain": "ESP", "germany": "GER",
    "portugal": "POR", "england": "ENG", "netherlands": "NED", "belgium": "BEL",
    "japan": "JPN", "uruguay": "URU", "croatia": "CRO", "norway": "NOR",
    "iraq": "IRQ", "paraguay": "PAR",
}


def _norm_name(name: str) -> str:
    s = name.strip().lower()
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z ]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def is_mapped(name: str) -> bool:
    """True if `name` has an explicit code in _TEAM_CODES (i.e. won't hit the
    first-3-letters fallback). Callers warn on unmapped names because the fallback
    can silently break the cross-source join."""
    return _norm_name(name) in _TEAM_CODES


def team_code(name: str) -> str:
    """3-letter code for a team. Falls back to first 3 alpha chars, uppercased,
    when the team isn't in the map (logged by callers; safe for ids but add the
    real code to _TEAM_CODES to guarantee a clean cross-source join)."""
    norm = _norm_name(name)
    if norm in _TEAM_CODES:
        return _TEAM_CODES[norm]
    letters = re.sub(r"[^A-Za-z]", "", name).upper()
    return letters[:3] or "XXX"


def slugify_case_id(commence_time: str, home_team: str, away_team: str) -> str:
    """wc26_<YYYYMMDD>_<HOMECODE>_<AWAYCODE>."""
    date = commence_time[:10].replace("-", "")
    return f"wc26_{date}_{team_code(home_team)}_{team_code(away_team)}"


def match_key(commence_time: str, home_team: str, away_team: str) -> tuple:
    """Order-independent join key: (date, frozenset{codeA, codeB}).

    Used to back-fill odds/results onto a seeded case even if the-odds-api lists
    the fixture with home/away swapped relative to how it was seeded.
    """
    date = commence_time[:10]
    return (date, frozenset({team_code(home_team), team_code(away_team)}))


# --- pure parsing ----------------------------------------------------------

def _avg_h2h_prices(event: dict) -> dict | None:
    """Average decimal h2h prices across all bookmakers -> {home,draw,away}.

    Returns None if no bookmaker carries an h2h market for this event.
    """
    home, away = event["home_team"], event["away_team"]
    buckets = {"home": [], "draw": [], "away": []}
    for bk in event.get("bookmakers") or []:
        for mk in bk.get("markets") or []:
            if mk.get("key") != "h2h":
                continue
            for oc in mk.get("outcomes") or []:
                name, price = oc.get("name"), oc.get("price")
                if price is None:
                    continue
                if name == home:
                    buckets["home"].append(float(price))
                elif name == away:
                    buckets["away"].append(float(price))
                elif name == "Draw":
                    buckets["draw"].append(float(price))
    if not all(buckets[k] for k in ("home", "draw", "away")):
        return None
    return {k: round(sum(v) / len(v), 4) for k, v in buckets.items()}


def parse_odds_event(event: dict) -> dict | None:
    """Normalize one the-odds-api odds event. None if no usable h2h odds."""
    odds = _avg_h2h_prices(event)
    if odds is None:
        return None
    return {
        "id": event["id"],
        "home_team": event["home_team"],
        "away_team": event["away_team"],
        "commence_time": event["commence_time"],
        "odds": odds,
    }


def parse_scores_event(event: dict) -> dict | None:
    """Decide home/draw/away from a completed scores event. None if not done.

    Returns the raw teams too, so callers can join by match_key.
    """
    if not event.get("completed"):
        return None
    scores = event.get("scores") or []
    by_name = {s["name"]: int(s["score"]) for s in scores if s.get("score") is not None}
    home, away = event["home_team"], event["away_team"]
    if home not in by_name or away not in by_name:
        return None
    hs, as_ = by_name[home], by_name[away]
    result = "home" if hs > as_ else "away" if as_ > hs else "draw"
    return {
        "id": event["id"],
        "home_team": home,
        "away_team": away,
        "commence_time": event.get("commence_time", ""),
        "result": result,
        "home_score": hs,
        "away_score": as_,
    }


# --- network (not unit-tested; exercised by snapshot.py / grade.py) ---------

def _get(path: str, params: dict) -> list:
    url = f"{_BASE}{path}?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310 (trusted host)
        return json.loads(resp.read().decode())


def fetch_odds(api_key: str) -> list:
    """Upcoming WC fixtures with decimal h2h odds (EU + UK + US books)."""
    return _get(f"/sports/{SPORT}/odds", {
        "apiKey": api_key, "regions": "eu,uk,us",
        "markets": "h2h", "oddsFormat": "decimal",
    })


def fetch_scores(api_key: str, days_from: int = 3) -> list:
    """Recently completed (and live) WC fixtures with scores."""
    return _get(f"/sports/{SPORT}/scores", {
        "apiKey": api_key, "daysFrom": str(days_from),
    })
