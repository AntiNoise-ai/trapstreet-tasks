# Case protocol

*Addressed to the solution author. Your agent never reads this file -- it
sees `step1.txt` or `step2.txt` as its prompt, one per session.*

This case has TWO steps and they must run as TWO SEPARATE SESSIONS of your
harness. That separation is the entire point of the task.

1. Run `step1.txt` as the prompt for a session. It gives the agent a table
   and asks it to compute one value and remember it.
2. Run `step2.txt` as the prompt for a **fresh session**. It asks for that
   value. The table is not repeated.

**Use `tools/run_case.sh` and none of the rules below can be violated by
accident.** It reads `TRAP_MANIFEST`, runs both sessions with the isolation
this task requires, scrubs the manifest from both, and prints only session
2's stdout. Write it by hand only if your harness cannot be invoked as
`<command> "<prompt>"`.

It ships with the task, not with your solution, and `cmd` runs in your
solution's directory — so give the checkout a stable address with
`clone_to`. The task README has the four-line recipe.

## Rules

- Step 2 MUST be a new session, not a continuation or a resume of step 1.
  Reusing or resuming session 1 tests your harness's session continuation,
  not its memory across sessions, and is not what this task measures.
- **Step 2's working directory must not reach step 1's files.** Run the two
  steps in unrelated directories, and do not leave `step1.txt`, a copy of
  the table, or step 1's captured output anywhere step 2 can walk to. This
  is not a formality: a stock agent given a sibling directory *will* run
  `ls ..`, find `step1.txt`, and recompute the answer from the table
  instead of recalling it. That scores 1.0 and measures nothing.
- Your solution's stdout is what gets scored, and only step 2's answer
  belongs there. Print the value on the last non-empty line.
- Nothing forbids you from carrying the value yourself instead of letting
  your agent remember it -- but see "Known limitations" in the task README.
  Solutions are public.

## Output

The last non-empty line of stdout must be the value from step 2, alone.
If your solution has no value to report, print `UNKNOWN`.
