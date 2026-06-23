"""Run-level grader for the worldcup_betting task.

Aggregates per-case judge metrics into the leaderboard verdict. Models are RANKED
by mean_log_loss (lower is better) — the primary signal, because the model
predicted blind and calibration converges faster than ROI on small samples.

  - mean_log_loss  : ranking key — average calibration loss (lower better).
  - mean_brier     : bounded calibration loss, robust on tiny samples.
  - accuracy       : fraction of graded matches whose winner the model called.
  - roi            : Σprofit / Σstaked over cases that have odds. Value-betting
                     diagnostic; null until odds are back-filled. On a sharp market
                     + small sample most models run slightly negative — ROI only
                     separates the field at scale (~50+ matches).
  - passed         : coarse roi>0 flag (beat the line at all), NOT the ranking.
  - n_graded       : matches played + judged.
  - n_pending      : fixtures snapshotted but not yet played (score is null).
  - n_with_odds    : graded matches that had odds available for ROI.
"""
from __future__ import annotations

import json
import os


def _mean(xs):
    return (sum(xs) / len(xs)) if xs else None


def main() -> None:
    cases = json.loads(os.environ["TRAPTASK_PAYLOAD"])

    graded = [c for c in cases
              if c.get("metrics") and c["metrics"].get("score") is not None]
    pending = [c for c in cases
               if not c.get("metrics") or c["metrics"].get("score") is None]

    log_losses = [c["metrics"]["log_loss"] for c in graded
                  if c["metrics"].get("log_loss") is not None]
    briers = [c["metrics"]["brier"] for c in graded
              if c["metrics"].get("brier") is not None]
    mean_log_loss = _mean(log_losses)
    mean_brier = _mean(briers)
    # fraction whose argmax outcome was the actual winner. Biased LOW: a model's
    # argmax is almost never "draw", so drawn matches score ~0 here. Read as
    # "called the winner", not overall correctness.
    winner_accuracy = _mean([c["metrics"]["score"] for c in graded])

    with_odds = [c for c in graded if c["metrics"].get("staked") is not None]
    total_staked = sum(c["metrics"].get("staked", 0.0) or 0.0 for c in with_odds)
    total_profit = sum(c["metrics"].get("profit", 0.0) or 0.0 for c in with_odds)
    roi = (total_profit / total_staked) if total_staked > 0 else None

    n_bets_won = sum(1 for c in with_odds if (c["metrics"].get("profit", 0.0) or 0.0) > 0)
    n_bets_placed = sum(1 for c in with_odds if (c["metrics"].get("staked", 0.0) or 0.0) > 0)

    durations = [c.get("duration", 0.0) for c in cases if c.get("duration") is not None]
    latency_ms_total = round(sum(durations) * 1000, 1) if durations else 0.0

    passed = bool(graded) and roi is not None and roi > 0.0

    print(json.dumps({
        "passed": passed,
        "rank_key": round(mean_log_loss, 6) if mean_log_loss is not None else None,
        "mean_log_loss": round(mean_log_loss, 6) if mean_log_loss is not None else None,
        "mean_brier": round(mean_brier, 6) if mean_brier is not None else None,
        "winner_accuracy": round(winner_accuracy, 4) if winner_accuracy is not None else None,
        "roi": round(roi, 6) if roi is not None else None,
        "total_staked": round(total_staked, 4),
        "total_profit": round(total_profit, 4),
        "n_graded": len(graded),
        "n_pending": len(pending),
        "n_with_odds": len(with_odds),
        "n_bets_placed": n_bets_placed,
        "n_bets_won": n_bets_won,
        "latency_ms_total": latency_ms_total,
    }))


if __name__ == "__main__":
    main()
