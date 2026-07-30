# tests/test_judge.py
import json
import sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import judge  # noqa: E402

EXPECTED = {
    "id": "case_01",
    "bug_category": "off_by_one",
    "file_path": "src/croniter/croniter.py",
    "buggy_line": 1276,
    "line_tolerance": 2,
    "keywords": ["off-by-one", "1-based", "modulo", "boundary condition", "wrong range"],
}


def _out(findings):
    return json.dumps({"findings": findings})


def test_exact_hit_scores_one():
    out = _out([{"file": "croniter.py", "line": 1276,
                 "description": "classic off-by-one: 1-based month uses raw modulo"}])
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 1.0 and r["hit_index"] == 0


def test_near_miss_within_tolerance_hits():
    out = _out([{"file": "croniter.py", "line": 1277,
                 "description": "off-by-one in the month bound"}])
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 1.0


def test_line_outside_tolerance_misses():
    out = _out([{"file": "croniter.py", "line": 1300,
                 "description": "off-by-one modulo issue"}])
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 0.0


def test_wrong_file_misses():
    out = _out([{"file": "other_file.py", "line": 1276,
                 "description": "off-by-one modulo issue"}])
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 0.0


def test_missing_keyword_misses():
    out = _out([{"file": "croniter.py", "line": 1276,
                 "description": "this returns the wrong value sometimes"}])
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 0.0
    assert r["best_match_signals"]["file_match"] is True
    assert r["best_match_signals"]["line_match"] is True
    assert r["best_match_signals"]["keyword_match"] is False


def test_hit_beyond_first_five_ignored_anti_shotgun():
    padding = [{"file": "x.py", "line": i, "description": "unrelated"} for i in range(5)]
    real_hit = {"file": "croniter.py", "line": 1276, "description": "off-by-one modulo issue"}
    out = _out(padding + [real_hit])
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 0.0
    assert r["n_findings_considered"] == 5


def test_hit_within_first_five_counts():
    padding = [{"file": "x.py", "line": i, "description": "unrelated"} for i in range(4)]
    real_hit = {"file": "croniter.py", "line": 1276, "description": "off-by-one modulo issue"}
    out = _out(padding + [real_hit])
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 1.0 and r["hit_index"] == 4


def test_malformed_json():
    r = judge.score_case("I think the bug is on line 1276", EXPECTED)
    assert r["score"] == 0.0 and r["format_ok"] is False


def test_fenced_json_parses():
    inner = _out([{"file": "croniter.py", "line": 1276, "description": "off-by-one modulo issue"}])
    out = "```json\n" + inner + "\n```"
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 1.0


def test_missing_findings_key():
    r = judge.score_case('{"review": "looks fine"}', EXPECTED)
    assert r["score"] == 0.0 and r["format_ok"] is False


def test_non_dict_finding_entries_ignored_not_crashed():
    out = _out(["just a string finding"])
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 0.0


def test_empty_findings_list():
    out = _out([])
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 0.0 and r["hit_index"] is None


# -- Regression tests: word-boundary keyword matching (case_02 "none" exploit) --

EXPECTED_CASE_02 = {
    "id": "case_02",
    "bug_category": "null_deref",
    "file_path": "Lib/gftools/push/trafficjam.py",
    "buggy_line": 535,
    "line_tolerance": 2,
    "keywords": ["nonetype", "missing null check", "typeerror", "not subscriptable"],
}


def test_generic_none_exploit_no_longer_scores_hit():
    """Reproduces the reviewer's exploit: a boilerplate finding containing the
    generic word "none" used to false-positive-match case_02's old keyword
    list even though it shows no real understanding of the bug. Now that
    "none" has been dropped from the keywords, this must score 0.0."""
    out = _out([{
        "file": "trafficjam.py",
        "line": 535,
        "description": "none of the edge cases here are obviously handled",
    }])
    r = judge.score_case(out, EXPECTED_CASE_02)
    assert r["score"] == 0.0
    assert r["best_match_signals"]["keyword_match"] is False


def test_word_boundary_matching_avoids_substring_false_positive():
    """A keyword like "race" must not match inside an unrelated longer word
    like "embrace" -- confirms _finding_matches uses \\b-anchored regex, not
    raw substring containment."""
    expected = {
        "id": "synthetic",
        "bug_category": "race_condition",
        "file_path": "src/foo.py",
        "buggy_line": 10,
        "line_tolerance": 2,
        "keywords": ["race"],
    }
    out = _out([{
        "file": "foo.py",
        "line": 10,
        "description": "callers should embrace this pattern going forward",
    }])
    r = judge.score_case(out, expected)
    assert r["score"] == 0.0
    assert r["best_match_signals"]["keyword_match"] is False


def test_word_boundary_matching_still_matches_standalone_keyword():
    expected = {
        "id": "synthetic",
        "bug_category": "race_condition",
        "file_path": "src/foo.py",
        "buggy_line": 10,
        "line_tolerance": 2,
        "keywords": ["race"],
    }
    out = _out([{
        "file": "foo.py",
        "line": 10,
        "description": "classic race condition between the two threads",
    }])
    r = judge.score_case(out, expected)
    assert r["score"] == 1.0


# -- Regression test: RecursionError on deeply-nested JSON must degrade gracefully --

def test_deeply_nested_json_does_not_raise_recursion_error():
    nested = "{\"x\": " * 5000 + "1" + "}" * 5000
    r = judge.score_case(nested, EXPECTED)
    assert r == {
        "score": 0.0,
        "hit_index": None,
        "n_findings_considered": 0,
        "format_ok": False,
        "reason": "output is not valid JSON",
    }


# -- Regression test: Infinity/NaN line values must degrade gracefully --
#
# json.loads accepts the non-standard literals Infinity/-Infinity/NaN by
# default, parsing them to float("inf")/float("-inf")/float("nan"). A
# solution can therefore emit valid-per-json.loads output like
# {"findings": [{"file": "x.py", "line": Infinity, "description": "..."}]}.
# int(float("inf")) raises OverflowError and int(float("nan")) raises
# ValueError -- both must be caught in _finding_matches so this degrades to
# a clean miss instead of crashing score_case().

def test_infinity_line_value_does_not_crash_and_misses():
    out = _out([{
        "file": "croniter.py",
        "line": float("inf"),
        "description": "classic off-by-one: 1-based month uses raw modulo",
    }])
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 0.0
    assert r["best_match_signals"]["line_match"] is False


def test_negative_infinity_line_value_does_not_crash_and_misses():
    out = _out([{
        "file": "croniter.py",
        "line": float("-inf"),
        "description": "classic off-by-one: 1-based month uses raw modulo",
    }])
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 0.0
    assert r["best_match_signals"]["line_match"] is False


def test_nan_line_value_does_not_crash_and_misses():
    out = _out([{
        "file": "croniter.py",
        "line": float("nan"),
        "description": "classic off-by-one: 1-based month uses raw modulo",
    }])
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 0.0


# -- regression: real-world phrasings that were false negatives -------------
#
# Found by hand-checking real solution outputs (jeffallan/alireza/awesome/
# baseline-no-skill code-review solutions) against gold.cases.json's keyword
# lists: each of these is a phrasing a real model actually produced for the
# correct bug, on the correct file/line, that the ORIGINAL keyword list
# failed to recognize. Not theorized in advance -- these are the exact
# sentences that were scored 0 before this fix.

def _expected_for(case_id: str) -> dict:
    here = pathlib.Path(__file__).resolve().parents[1]
    return json.loads((here / "expected" / case_id / "answer.json").read_text())


def test_case01_realworld_phrasing_no_plus_one_correction():
    """awesome's actual output: named the exact right mechanism (missing +1
    correction, value escapes the 1-12 range) without ever saying
    'off-by-one' or '1-based'."""
    out = _out([{
        "file": "croniter.py", "line": 1276,
        "description": "unlike the day field there is no `+1` correction to keep the result in the valid 1-12 range.",
    }])
    r = judge.score_case(out, _expected_for("case_01"))
    assert r["score"] == 1.0


def test_case06_realworld_phrasing_bypassing_secret_auth():
    """jeffallan's actual output: correctly described routes being exposed
    without the secret-path protection, without ever using the words
    'authentication' or 'unauthenticated'."""
    out = _out([{
        "file": "settings_ui.py", "line": 3044,
        "description": "registers all routes with an empty prefix, exposing the settings UI without requiring the secret path, bypassing the secret-based auth.",
    }])
    r = judge.score_case(out, _expected_for("case_06"))
    assert r["score"] == 1.0


def test_case08_realworld_phrasing_should_be_narrowed():
    """jeffallan's actual output: correctly identified the except clause as
    needing narrowing (implying it's currently too broad) without using
    'too broad' or 'bare except' literally."""
    out = _out([{
        "file": "_vrt.py", "line": 359,
        "description": "catching bare Exception and merely warning can mask genuine programming errors; the except should be narrowed to IO/read errors.",
    }])
    r = judge.score_case(out, _expected_for("case_08"))
    assert r["score"] == 1.0


def test_case08_realworld_phrasing_broadest_hiding_real_defects():
    """alireza's actual output split across 3 findings: the finding whose
    file+line exactly matched the bug used 'broadest `Exception` type' and
    'hiding real defects' -- neither literal phrase was in the original
    keyword list, so the exact-line finding scored a keyword miss while a
    different (wrong-line) finding scored a keyword hit, and no single
    finding had all three signals -- a false negative despite the model
    pinpointing the right file/line."""
    out = _out([{
        "file": "_vrt.py", "line": 359,
        "description": "Catching the broadest `Exception` type where a specific I/O error is appropriate means unrelated bugs are silently downgraded to warnings and skipped, hiding real defects.",
    }])
    r = judge.score_case(out, _expected_for("case_08"))
    assert r["score"] == 1.0


def test_case09_realworld_phrasing_raises_a_keyerror():
    """alireza's/awesome's actual output: correctly described cache.pop()
    raising KeyError for an absent key, phrased as 'raises a KeyError'
    rather than the original list's 'pop raises keyerror'."""
    out = _out([{
        "file": "calc.py", "line": 126,
        "description": "invalidate() calls cache.pop() without a default value, so it raises a KeyError if the key is not present in the cache.",
    }])
    r = judge.score_case(out, _expected_for("case_09"))
    assert r["score"] == 1.0


def test_case10_realworld_phrasing_discarding_all_subsecond_precision():
    """All four solutions independently described this exact mechanism as
    'discarding all sub-second precision' -- the original list only had
    'sub-second precision discarded' (reversed word order), a pure
    word-order near-miss on an otherwise fully correct answer."""
    out = _out([{
        "file": "api.py", "line": 186,
        "description": "int(fake_time()) truncates the fractional part before multiplying by 1e9, discarding all sub-second precision.",
    }])
    r = judge.score_case(out, _expected_for("case_10"))
    assert r["score"] == 1.0


# -- regression: the 3 cases replaced 2026-07-30 for being non-discriminating
# (case_03/07 were "textbook famous" -- every solution incl. a bare model
# solved them instantly; case_04 required niche async/event-loop intuition
# few solutions actually had). Each replacement is a real historical bugfix
# commit, same sourcing bar as the original 10 cases.

def test_case03_new_elif_short_circuit_correct_answer_scores_one():
    """Replacement for the old case_03 (a two-term != or or tautology,
    solved instantly by every solution incl. baseline). New bug:
    rsinger86/drf-access-policy's elif chain stops on the first matching
    principal keyword even if that keyword's own check fails, never
    falling through to check other principal types in the same list."""
    out = _out([{
        "file": "access_policy.py", "line": 102,
        "description": "the elif chain stops evaluating as soon as one principal keyword matches, even if that keyword's own check fails, so it never falls through to check other principal types present in the same list -- wrongly denies access it should grant.",
    }])
    r = judge.score_case(out, _expected_for("case_03"))
    assert r["score"] == 1.0


def test_case04_new_stale_closure_correct_answer_scores_one():
    """Replacement for the old case_04 (race_condition, required niche
    async/event-loop intuition every solution missed). New bug:
    litl/backoff's nonlocal reassignment permanently freezes max_tries
    after the first call to the decorated function."""
    out = _out([{
        "file": "_sync.py", "line": 34,
        "description": "max_tries is declared nonlocal and reassigned to the resolved value -- because of nonlocal this mutates the enclosing scope, so it's only resolved on the first call to the decorated function and every later call reuses that value.",
    }])
    r = judge.score_case(out, _expected_for("case_04"))
    assert r["score"] == 1.0


def test_case07_new_sql_injection_correct_answer_scores_one():
    """Replacement for the old case_07 (mutable default argument -- the
    single most textbook-famous Python gotcha, solved instantly by every
    solution incl. baseline). New bug: kolibri's filter_in_lesson
    interpolates a user-controlled id into raw SQL via .format()."""
    out = _out([{
        "file": "api.py", "line": 250,
        "description": "pk is interpolated directly into a raw SQL fragment via string formatting rather than parameterized, and pk is user-controlled -- a classic SQL injection vector, since a value containing a quote could break out of the string literal.",
    }])
    r = judge.score_case(out, _expected_for("case_07"))
    assert r["score"] == 1.0


def test_case03_realworld_phrasing_line_outside_old_tolerance():
    """baseline's actual output (2026-07-30 live run): named the exact
    mechanism ('multiple principal types', exact keyword hit) but cited
    line 109 (the id_prefix elif branch) -- 7 lines past the old buggy_line
    102 +/- 6 window. The bug is a structural property of the whole elif
    chain (lines ~99-118), so any branch's line is a valid citation;
    tolerance widened from 6 to 17 to cover the full chain."""
    out = _out([{
        "file": "access_policy.py", "line": 109,
        "description": "Using elif chains means principal matching is mutually exclusive; a statement listing multiple principal types only evaluates the first matching branch, so a user could be wrongly denied if they match a later branch but the earlier keyword branch evaluates False.",
    }])
    r = judge.score_case(out, _expected_for("case_03"))
    assert r["score"] == 1.0


def test_case03_realworld_phrasing_multiple_principals_never_reached():
    """awesome's actual output: right line (101, within tolerance) but
    phrased as 'multiple principals' / 'incorrectly denying access' /
    'never reached' -- none of which were literal substrings of the
    original keyword list despite being an exact description of the bug."""
    out = _out([{
        "file": "access_policy.py", "line": 101,
        "description": "The elif chain checks principal categories in mutually exclusive order, so a statement listing multiple principals only evaluates the first matching branch; the role/user-id checks in later branches are never reached, incorrectly denying access.",
    }])
    r = judge.score_case(out, _expected_for("case_03"))
    assert r["score"] == 1.0


def test_case04_realworld_phrasing_overwritten_with_called_results():
    """baseline's actual output: correctly described the nonlocal freeze
    mechanism ('overwritten with their called results on the first
    invocation', 'closure state ... rather than re-evaluated fresh each
    time') without using any of the original list's literal phrases."""
    out = _out([{
        "file": "_sync.py", "line": 33,
        "description": "The nonlocal declaration causes these values to be overwritten with their called results on the first invocation; the nonlocal mutation makes the closure state shared/corrupted across invocations rather than re-evaluated fresh each time.",
    }])
    r = judge.score_case(out, _expected_for("case_04"))
    assert r["score"] == 1.0


def test_case04_realworld_phrasing_shared_nonlocal_state():
    """awesome's actual output: 'overwrites the closure variables on the
    first call' / 'receive the already-resolved ... values' / 'mutating
    the shared nonlocal state' -- again none of the original literal
    phrases, despite pinpointing the exact right mechanism."""
    out = _out([{
        "file": "_sync.py", "line": 33,
        "description": "The nonlocal reassignment overwrites the closure variables on the first call, so subsequent invocations receive the already-resolved values instead of re-calling the callables. Each call should use a local variable rather than mutating the shared nonlocal state.",
    }])
    r = judge.score_case(out, _expected_for("case_04"))
    assert r["score"] == 1.0
