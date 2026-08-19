#!/usr/bin/env bash
# Reference runner for session_memory_recall -- ships WITH the task because
# the two-session protocol is the task. Prose rules ("run the steps in
# unrelated directories") do not survive contact with many entrants: the
# natural wrapper puts the two steps side by side, session 2 runs `ls ..`,
# finds step1.txt, recomputes the answer and scores 1.0 having recalled
# nothing. Use this runner unmodified and that failure is impossible.
#
# Usage, from your solution's trap.yaml `cmd`:
#
#   bash tools/run_case.sh <your-harness-command> [args...]
#
# Your command is invoked twice, with the prompt appended as the final
# argument, and must print the harness's reply to stdout:
#
#   <your-harness-command> [args...] "<prompt text>"
#
# Examples:
#   bash tools/run_case.sh dsh --profile my-profile
#   bash tools/run_case.sh claude -p
#   bash tools/run_case.sh python3 my_agent.py --model whatever
#
# What it guarantees:
#   - session 1 runs in its own temp dir, and that dir plus everything
#     session 1 wrote is DESTROYED before session 2 starts
#   - session 2 runs in a fresh temp dir that never contained step 1's
#     files and has no path relationship to them
#   - session 1's stdout goes to /dev/null, so it cannot be scored and
#     cannot be found on disk
#   - TRAP_MANIFEST is scrubbed from both sessions -- see below
#   - only session 2's stdout reaches the judge
set -uo pipefail

if [ "$#" -lt 1 ]; then
    echo "usage: run_case.sh <harness-command> [args...]" >&2
    exit 2
fi

: "${TRAP_MANIFEST:?run_case.sh must run under trap (TRAP_MANIFEST unset)}"

INPUTS_DIR=$(python3 -c '
import json, os, sys
m = json.loads(os.environ["TRAP_MANIFEST"])
sys.stdout.write(m["inputs_dir"])
') || { echo "could not read inputs_dir from TRAP_MANIFEST" >&2; exit 2; }

STEP1="$INPUTS_DIR/step1.txt"
STEP2="$INPUTS_DIR/step2.txt"
for f in "$STEP1" "$STEP2"; do
    [ -r "$f" ] || { echo "missing or unreadable: $f" >&2; exit 2; }
done

# Both sessions run without TRAP_MANIFEST. It names inputs_dir, step1.txt
# lives in it, and expected/answer.json is two levels above it -- so leaving
# it in the environment hands session 2 the table, or the gold answer itself,
# in a single read. That is the failure the two temp dirs exist to prevent,
# arriving by a shorter route, and it was live until a protocol test caught
# it. Scrubbing it also leaves session 2 without its own case id, which is
# what stops a solution that goes looking for the task checkout on disk from
# knowing which case_NN under it is the one it was asked about.
# The runner has already read the manifest above; the harness never needs it.
#
# Scrubbing is by VALUE, not by name: trap.yaml's `manifest_envvar` lets a
# solution call the variable whatever it likes (it only defaults to
# TRAP_MANIFEST), so unsetting the two names everyone expects would leave a
# renamed one holding the same path. Any exported variable whose value names
# an inputs_dir goes.
SCRUB=(-u TRAP_MANIFEST -u TRAPTASK_MANIFEST)
for _name in $(compgen -e); do
    case "${!_name-}" in *'"inputs_dir"'*) SCRUB+=(-u "$_name");; esac
done
harness() { env "${SCRUB[@]}" "$@"; }

SESSION1_DIR=$(mktemp -d "${TMPDIR:-/tmp}/smr-s1.XXXXXXXX")
SESSION2_DIR=$(mktemp -d "${TMPDIR:-/tmp}/smr-s2.XXXXXXXX")
cleanup() { rm -rf "$SESSION1_DIR" "$SESSION2_DIR"; }
trap cleanup EXIT INT TERM

# --- session 1: compute and commit to memory. Output is deliberately
# discarded -- if it were kept anywhere reachable, session 2 would read it.
(
    cd "$SESSION1_DIR" || exit 1
    harness "$@" "$(cat "$STEP1")"
) >/dev/null 2>&1
S1_STATUS=$?

# Destroy session 1's world BEFORE session 2 exists. This ordering is the
# whole isolation guarantee -- there is nothing left for session 2 to find.
rm -rf "$SESSION1_DIR"

if [ "$S1_STATUS" -ne 0 ]; then
    echo "session 1 exited $S1_STATUS" >&2
    # Still run session 2: a harness that failed step 1 should score 0 via
    # UNKNOWN rather than via a non-zero exit, which is less diagnostic.
fi

# --- session 2: recall. Its stdout is the solution's stdout.
(
    cd "$SESSION2_DIR" || exit 1
    harness "$@" "$(cat "$STEP2")"
)
