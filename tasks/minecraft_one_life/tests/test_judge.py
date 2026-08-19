import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import judge  # noqa: E402

EXPECTED = json.loads((ROOT / "expected" / "one_life" / "expected.json").read_text())


def run(**fields):
    base = {"obtained": False, "item": "diamond", "count": 0, "inventory": [],
            "milestones": [], "deaths": 0, "video": "", "seed": "s", "mc_version": "1.20.4"}
    base.update(fields)
    return judge.evaluate(json.dumps(base), EXPECTED, 0)


def test_survived_to_diamond_scores_one():
    r = run(obtained=True, count=1, inventory=["diamond x1"], deaths=0)
    assert r["score"] == 1.0 and r["died"] is False


def test_survived_to_stone_pickaxe_scores_point_four():
    assert run(inventory=["stone_pickaxe x1"], deaths=0)["score"] == 0.4


# The point of the board: a death truncates the run, and everything the agent
# picked up on its second life is off the record.
def test_death_caps_the_score_at_what_was_reached():
    r = run(inventory=["iron_pickaxe x1"], deaths=1,
            milestones_at_death=["wooden_pickaxe", "stone_pickaxe"])
    assert r["score"] == 0.4, "final inventory must not count once the agent died"
    assert r["died"] is True


# The shape a dishonest-or-careless report actually takes: die early, respawn,
# grind to a diamond, and report the diamond.
def test_diamond_obtained_after_dying_does_not_count():
    r = run(obtained=True, count=3, inventory=["diamond x3", "iron_pickaxe x1"],
            milestones=["diamond", "iron_pickaxe"], deaths=2,
            milestones_at_death=["wooden_pickaxe"])
    assert r["score"] == 0.2
    assert r["goal_met"] is False


def test_death_without_milestones_at_death_is_malformed():
    r = run(inventory=["diamond x1"], obtained=True, count=1, deaths=1)
    assert r["score"] == 0.0 and r["format_ok"] is False
    assert "milestones_at_death" in r["reason"]


def test_missing_deaths_field_is_malformed_on_a_one_life_task():
    out = json.dumps({"obtained": True, "item": "diamond", "count": 1,
                      "inventory": ["diamond x1"], "video": ""})
    r = judge.evaluate(out, EXPECTED, 0)
    assert r["score"] == 0.0 and r["format_ok"] is False


def test_no_video_still_scores():
    r = run(obtained=True, count=1, inventory=["diamond x1"], deaths=0, video="")
    assert r["score"] == 1.0 and r["video_declared"] is False


# Discrimination, checked for free: a weak-but-earnest run and a strong one must
# land far apart. This is the measured pair -- easy difficulty reached an iron
# pickaxe and then died, peaceful reached a diamond untouched.
def test_weak_and_strong_runs_are_far_apart():
    weak = run(inventory=["iron_pickaxe x1"], deaths=1, milestones_at_death=["stone_pickaxe"])
    strong = run(obtained=True, count=1, inventory=["diamond x1"], deaths=0)
    assert strong["score"] - weak["score"] >= 0.5
