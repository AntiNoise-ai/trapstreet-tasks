import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent


def run_grader(cases):
    env = {"TRAPTASK_PAYLOAD": json.dumps(cases), "PATH": "/usr/bin:/bin"}
    out = subprocess.run(
        [sys.executable, "grader.py"], cwd=HERE, env=env,
        capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout)


def _case(profit, staked, log_loss, score, brier=0.4):
    return {"metrics": {"profit": profit, "staked": staked, "log_loss": log_loss,
                        "brier": brier, "score": score}, "duration": 0.1}


def _case_no_odds(log_loss, score, brier=0.4):
    # graded on calibration but odds not yet back-filled (no staked/profit)
    return {"metrics": {"log_loss": log_loss, "brier": brier, "score": score},
            "duration": 0.1}


def test_roi_positive_passes():
    cases = [_case(1.1, 1.0, 0.5, 1.0), _case(-1.0, 1.0, 0.9, 0.0),
             _case(2.6, 2.0, 0.4, 1.0)]
    res = run_grader(cases)
    assert res["roi"] == 0.675           # 2.7 / 4.0
    assert res["total_staked"] == 4.0
    assert res["passed"] is True


def test_roi_negative_fails():
    cases = [_case(-1.0, 1.0, 1.2, 0.0), _case(-1.0, 1.0, 1.5, 0.0)]
    res = run_grader(cases)
    assert res["roi"] == -1.0
    assert res["passed"] is False


def test_calibration_and_accuracy_reported():
    cases = [_case(0.0, 0.0, 0.4, 1.0, brier=0.3),
             _case(0.0, 0.0, 0.6, 0.0, brier=0.5)]
    res = run_grader(cases)
    assert res["mean_log_loss"] == 0.5
    assert res["mean_brier"] == 0.4
    assert res["winner_accuracy"] == 0.5
    # both abstained -> no staked -> roi None, not a crash, not passed
    assert res["roi"] is None
    assert res["passed"] is False


def test_odds_pending_still_ranks_on_calibration():
    cases = [_case_no_odds(0.5, 1.0), _case_no_odds(0.7, 0.0)]
    res = run_grader(cases)
    assert res["n_graded"] == 2
    assert res["n_with_odds"] == 0
    assert res["rank_key"] == 0.6      # mean log-loss still defined
    assert res["roi"] is None


def test_ungraded_cases_skipped():
    cases = [_case(1.1, 1.0, 0.5, 1.0),
             {"metrics": {"score": None, "reason": "match not yet graded"}, "duration": 0.0}]
    res = run_grader(cases)
    assert res["n_graded"] == 1
    assert res["n_pending"] == 1
