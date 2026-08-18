# `harness:` — what a solution's harness must be able to do

A board is useless to someone whose harness physically cannot attempt it. Today
nothing on the task says so, and the mismatch only shows up as a failed run:
`minecraft_obtain_diamond` needs a game server and thirty minutes per case;
`session_memory_recall` needs two genuinely separate sessions; most tasks need
neither.

So a task declares what it demands, in `traptask.yaml`:

```yaml
harness:
  needs: [one_shot]
```

## Values

| Value | Meaning | Example |
|---|---|---|
| `one_shot` | One command, one prompt, print the answer, exit. | `ledger_close`, `python_bugfix_diff` |
| `multi_session` | The solution must start two or more sessions that do not share state. | `session_memory_recall` |
| `long_horizon` | A single case runs for tens of minutes. | `minecraft_obtain_diamond` |
| `external_service` | Something outside the harness must be stood up first. | a game server, a database |
| `media_capture` | The run must record video or images as evidence. | `minecraft_obtain_diamond` |

`needs` is a list; a task may declare several. Absent means `[one_shot]`.

## What this is not

It does **not** say which harnesses pass. A DeepSeek Harness `headless` profile
satisfies `one_shot` and cannot satisfy `multi_session` in the same profile --
but that is a fact about that profile, not about the task, and it changes as
harnesses change. The task states its own demands and stops there.

It is also not a permission gate. Nothing refuses a run because of this field.
It exists so a tool that recommends boards can avoid recommending one the user
has no way to attempt.
