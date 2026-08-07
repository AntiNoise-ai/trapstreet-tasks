"""Pytest tests for the CUAD judge (span_f1 + no_clause matchers)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).parent


def _load_judge():
    spec = importlib.util.spec_from_file_location("cuad_judge", HERE / "judge.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ----- answer extraction -----

def test_extract_plain_text():
    j = _load_judge()
    assert j.extract_agent_answer("  SUPPLY CONTRACT  ") == "SUPPLY CONTRACT"

def test_extract_json_answer():
    j = _load_judge()
    assert j.extract_agent_answer('{"answer": "SUPPLY CONTRACT"}') == "SUPPLY CONTRACT"

def test_extract_empty():
    j = _load_judge()
    assert j.extract_agent_answer("   ") == ""


# ----- token F1 -----

def test_token_f1_exact():
    j = _load_judge()
    assert j.token_f1("Supply Contract", "SUPPLY CONTRACT") == 1.0

def test_token_f1_articles_ignored():
    j = _load_judge()
    # "the" is dropped by SQuAD normalisation
    assert j.token_f1("the supply contract", "supply contract") == 1.0

def test_token_f1_no_overlap():
    j = _load_judge()
    assert j.token_f1("governing law new york", "supply contract") == 0.0

def test_token_f1_partial():
    j = _load_judge()
    f1 = j.token_f1("supply agreement contract", "supply contract")
    assert 0.0 < f1 < 1.0


# ----- span scoring -----

def test_span_score_containment_with_commentary():
    """Model quotes the clause verbatim but adds commentary → containment = 1.0."""
    j = _load_judge()
    pred = "The relevant clause is: Neither party may assign this Agreement without consent."
    gold = ["Neither party may assign this Agreement without consent"]
    score, _ = j.span_score(pred, gold)
    assert score == 1.0

def test_span_score_best_of_multiple():
    j = _load_judge()
    pred = "Governing law is the State of New York"
    gold = ["this Agreement shall be governed by Delaware law", "Governing law is the State of New York"]
    score, _ = j.span_score(pred, gold)
    assert score == 1.0

def test_span_score_miss():
    j = _load_judge()
    score, _ = j.span_score("NO CLAUSE FOUND", ["Neither party may assign this Agreement"])
    assert score < 0.5


# ----- span_f1 matcher (PRESENT cases) -----

def test_m_span_f1_pass():
    j = _load_judge()
    ok, _ = j.m_span_f1("SUPPLY CONTRACT", {"kind": "span_f1", "gold_spans": ["SUPPLY CONTRACT"], "threshold": 0.5})
    assert ok is True

def test_m_span_f1_laziness_fail():
    """The laziness test: saying 'no clause' when one exists must FAIL."""
    j = _load_judge()
    ok, _ = j.m_span_f1("NO CLAUSE FOUND", {"kind": "span_f1", "gold_spans": ["SUPPLY CONTRACT"], "threshold": 0.5})
    assert ok is False


# ----- no_clause matcher (ABSENT cases) -----

def test_m_no_clause_sentinel():
    j = _load_judge()
    ok, _ = j.m_no_clause("NO CLAUSE FOUND", {"kind": "no_clause"})
    assert ok is True

def test_m_no_clause_natural_language():
    j = _load_judge()
    for ans in ["This contract does not contain an Agreement Date clause.",
                "There is no such provision.",
                "None.",
                "N/A"]:
        ok, _ = j.m_no_clause(ans, {"kind": "no_clause"})
        assert ok is True, ans

def test_m_no_clause_hallucination_fail():
    """The hallucination test: fabricating a span when none exists must FAIL."""
    j = _load_judge()
    ok, _ = j.m_no_clause(
        "The Agreement Date is January 1, 2020 as stated in section 1.",
        {"kind": "no_clause"},
    )
    assert ok is False


# ----- run_matchers aggregation -----

def test_run_matchers_all_pass():
    j = _load_judge()
    score, results = j.run_matchers("SUPPLY CONTRACT", [{"kind": "span_f1", "gold_spans": ["SUPPLY CONTRACT"], "threshold": 0.5}])
    assert score == 1.0
    assert results[0]["pass"] is True

def test_run_matchers_unknown_kind_fails():
    j = _load_judge()
    score, results = j.run_matchers("x", [{"kind": "bogus"}])
    assert score == 0.0
    assert results[0]["pass"] is False
