"""Pytest tests for the agents-in-situationship judge."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
EXPECTED_PATH = HERE / "expected" / "baseline_20q" / "answer.json"


def load_expected() -> dict:
    return json.loads(EXPECTED_PATH.read_text())


def test_expected_file_loads():
    """Sanity: the expected/answer.json file we wrote is valid."""
    data = load_expected()
    assert data["n_questions"] == 20
    assert len(data["scoring_key"]) == 20
    assert data["primary_tiebreak_order"] == ["anxious", "avoidant", "secure"]
