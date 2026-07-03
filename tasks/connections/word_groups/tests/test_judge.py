# tests/test_judge.py
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import judge  # noqa: E402

EXPECTED = {
    "id": "h1", "category": "hard",
    "groups": [
        {"theme": "Card games",    "words": ["POKER", "BRIDGE", "WAR", "RUMMY"]},
        {"theme": "Card suits",    "words": ["HEARTS", "SPADES", "CLUBS", "DIAMONDS"]},
        {"theme": "BLACK ___",     "words": ["JACK", "BERRY", "SMITH", "OUT"]},
        {"theme": "Special cards", "words": ["KING", "QUEEN", "ACE", "JOKER"]},
    ],
}

PERFECT = '{"groups": [' \
    '{"theme": "games", "words": ["POKER", "BRIDGE", "WAR", "RUMMY"]},' \
    '{"theme": "suits", "words": ["HEARTS", "SPADES", "CLUBS", "DIAMONDS"]},' \
    '{"theme": "black", "words": ["JACK", "BERRY", "SMITH", "OUT"]},' \
    '{"theme": "cards", "words": ["KING", "QUEEN", "ACE", "JOKER"]}]}'


def test_perfect_scores_one():
    r = judge.score_case(PERFECT, EXPECTED)
    assert r["score"] == 1.0 and r["groups_correct"] == 4 and r["solved"] is True


def test_two_of_four():
    # last two groups swapped one word each -> only first two groups match
    out = '{"groups": [' \
        '{"theme": "g", "words": ["POKER", "BRIDGE", "WAR", "RUMMY"]},' \
        '{"theme": "s", "words": ["HEARTS", "SPADES", "CLUBS", "DIAMONDS"]},' \
        '{"theme": "x", "words": ["JACK", "BERRY", "SMITH", "KING"]},' \
        '{"theme": "y", "words": ["QUEEN", "ACE", "JOKER", "OUT"]}]}'
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 0.5 and r["groups_correct"] == 2 and r["solved"] is False


def test_scrambled_scores_zero():
    out = '{"groups": [' \
        '{"theme": "1", "words": ["POKER", "HEARTS", "JACK", "KING"]},' \
        '{"theme": "2", "words": ["BRIDGE", "SPADES", "BERRY", "QUEEN"]},' \
        '{"theme": "3", "words": ["WAR", "CLUBS", "SMITH", "ACE"]},' \
        '{"theme": "4", "words": ["RUMMY", "DIAMONDS", "OUT", "JOKER"]}]}'
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 0.0 and r["groups_correct"] == 0


def test_malformed_json():
    r = judge.score_case("i think the groups are cards and suits", EXPECTED)
    assert r["score"] == 0.0 and r["format_ok"] is False


def test_fenced_json_parses():
    fenced = "```json\n" + PERFECT + "\n```"
    r = judge.score_case(fenced, EXPECTED)
    assert r["score"] == 1.0


def test_theme_labels_ignored():
    # correct partition, nonsense themes -> still full credit
    r = judge.score_case(PERFECT.replace("games", "zzz").replace("suits", "qqq"), EXPECTED)
    assert r["score"] == 1.0


def test_case_and_whitespace_insensitive():
    out = '{"groups": [' \
        '{"theme": "g", "words": ["poker", " Bridge ", "WAR", "rummy"]},' \
        '{"theme": "s", "words": ["hearts", "spades", "clubs", "diamonds"]},' \
        '{"theme": "b", "words": ["jack", "berry", "smith", "out"]},' \
        '{"theme": "c", "words": ["king", "queen", "ace", "joker"]}]}'
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 1.0


def test_wrong_group_size_no_match():
    # a 5-word group can't equal any gold 4-set
    out = '{"groups": [' \
        '{"theme": "g", "words": ["POKER", "BRIDGE", "WAR", "RUMMY", "ACE"]},' \
        '{"theme": "s", "words": ["HEARTS", "SPADES", "CLUBS", "DIAMONDS"]},' \
        '{"theme": "b", "words": ["JACK", "BERRY", "SMITH", "OUT"]},' \
        '{"theme": "c", "words": ["KING", "QUEEN", "JOKER"]}]}'
    r = judge.score_case(out, EXPECTED)
    assert r["groups_correct"] == 2  # suits + black match; games(5) and special(3) do not


def test_extra_groups_score_but_not_solved():
    # 4 correct groups first, then a junk 5th group -> first-4 all correct so
    # groups_correct==4, but not a clean partition -> well_formed False, solved False.
    out = '{"groups": [' \
        '{"theme": "g", "words": ["POKER", "BRIDGE", "WAR", "RUMMY"]},' \
        '{"theme": "s", "words": ["HEARTS", "SPADES", "CLUBS", "DIAMONDS"]},' \
        '{"theme": "b", "words": ["JACK", "BERRY", "SMITH", "OUT"]},' \
        '{"theme": "c", "words": ["KING", "QUEEN", "ACE", "JOKER"]},' \
        '{"theme": "extra", "words": ["POKER", "HEARTS", "JACK", "KING"]}]}'
    r = judge.score_case(out, EXPECTED)
    assert r["groups_correct"] == 4
    assert r["well_formed"] is False
    assert r["solved"] is False


def test_shotgun_beyond_four_is_ignored():
    # First 4 groups are wrong (scrambled); the 2 correct groups sit at positions
    # 5-6 and must be ignored by the first-4 truncation -> groups_correct 0.
    out = '{"groups": [' \
        '{"theme": "1", "words": ["POKER", "HEARTS", "JACK", "KING"]},' \
        '{"theme": "2", "words": ["BRIDGE", "SPADES", "BERRY", "QUEEN"]},' \
        '{"theme": "3", "words": ["WAR", "CLUBS", "SMITH", "ACE"]},' \
        '{"theme": "4", "words": ["RUMMY", "DIAMONDS", "OUT", "JOKER"]},' \
        '{"theme": "5", "words": ["POKER", "BRIDGE", "WAR", "RUMMY"]},' \
        '{"theme": "6", "words": ["HEARTS", "SPADES", "CLUBS", "DIAMONDS"]}]}'
    r = judge.score_case(out, EXPECTED)
    assert r["groups_correct"] == 0
    assert r["solved"] is False


def test_perfect_is_well_formed():
    r = judge.score_case(PERFECT, EXPECTED)
    assert r["well_formed"] is True and r["solved"] is True
