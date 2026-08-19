"""End-to-end: tools/run_case.sh + judge.py, driven by stub harnesses.

This is the pre-launch floor/ceiling check. It answers the two questions
that decide whether the board means anything, and it answers them with no
model and no spend:

  floor   -- can a harness with no memory score above 0 by any route?
  ceiling -- can a harness that does carry state reach 1.0?

A task where the floor is not 0 measures nothing. A task where the ceiling
is not 1.0 is unpassable and measures nothing either.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import judge  # noqa: E402

RUNNER = ROOT / "tools" / "run_case.sh"
STUB = pathlib.Path(__file__).resolve().parent / "stub_harness.py"
ALL_CASES = sorted(p.name for p in (ROOT / "inputs").iterdir() if p.is_dir())


def run(case_id: str, mode: str, tmp_path=None, manifest_var: str = "TRAP_MANIFEST") -> str:
    """One case through the real runner, as trap-cli would invoke it."""
    manifest = json.dumps({"inputs_dir": str(ROOT / "inputs" / case_id)})
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(tmp_path or ROOT),
        "TRAP_MANIFEST": manifest,
    }
    if manifest_var != "TRAP_MANIFEST":
        env[manifest_var] = manifest
    if tmp_path is not None:
        env["STUB_MEMORY_FILE"] = str(tmp_path / "memory.txt")
    proc = subprocess.run(
        ["bash", str(RUNNER), sys.executable, str(STUB), mode],
        capture_output=True, text=True, env=env, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def score(case_id: str, stdout: str) -> float:
    expected = json.loads((ROOT / "expected" / case_id / "answer.json").read_text())
    return judge.score_case(stdout, expected)["score"]


# --- floor: every memoryless route must score 0 on every case ---

def test_a_harness_with_no_memory_scores_zero():
    assert [score(c, run(c, "amnesiac")) for c in ALL_CASES] == [0.0] * len(ALL_CASES)


def test_inventing_a_plausible_figure_scores_zero():
    assert [score(c, run(c, "confabulator")) for c in ALL_CASES] == [0.0] * len(ALL_CASES)


def test_neither_session_can_read_the_task_manifest():
    """TRAP_MANIFEST names inputs_dir, and step1.txt lives in it.

    Leaving it in the environment hands session 2 the table in one read --
    the exact failure the two temp dirs exist to prevent, arriving by a
    shorter route. `expected/` is two levels further up.
    """
    for case_id in ALL_CASES:
        out = run(case_id, "env_scavenger")
        assert out.strip() == "UNKNOWN", f"{case_id}: read the table via the manifest"
        assert score(case_id, out) == 0.0


def test_a_renamed_manifest_variable_is_scrubbed_too():
    """`manifest_envvar` is solution-configurable in trap.yaml (it defaults to
    TRAP_MANIFEST). Unsetting two known names would leave a solution that
    renamed its own variable holding the path to step1.txt."""
    for case_id in ALL_CASES:
        out = run(case_id, "env_scavenger", manifest_var="SOLUTION_PRIVATE_MANIFEST")
        assert out.strip() == "UNKNOWN", f"{case_id}: reached the table under a new name"
        assert score(case_id, out) == 0.0


def test_walking_out_of_the_working_directory_finds_nothing():
    """What a stock agent actually does when it senses a fresh session."""
    for case_id in ALL_CASES:
        out = run(case_id, "snooper")
        assert score(case_id, out) == 0.0


def test_printing_every_figure_scores_zero():
    assert [score(c, run(c, "shotgun")) for c in ALL_CASES] == [0.0] * len(ALL_CASES)


# --- ceiling: a harness that carries state reaches 1.0 ---

def test_a_harness_that_carries_state_scores_one_on_every_case(tmp_path):
    """Every derivation, not just the easy one: the voucher cases take a
    different path through the judge (VOUCHER_RE, no scrubbing, no
    four-digit filter) and would otherwise have a floor but no ceiling."""
    scores = [score(c, run(c, "remembers", tmp_path)) for c in ALL_CASES]
    assert scores == [1.0] * len(ALL_CASES), dict(zip(ALL_CASES, scores))
