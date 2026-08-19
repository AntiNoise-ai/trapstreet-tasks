# Task: One Life

Play a fresh **survival** Minecraft world with hostile mobs and climb as far up
the tech tree as you can. **Nothing you do after your first death counts.**

Read that literally. Minecraft does not stop when you die — you respawn on the
spot and can keep playing, and your inventory is lying wherever you fell. So
this is a scoring rule, not something the game enforces: you may carry on, and
none of it will score. A diamond mined on your second life is not a one-life
diamond.

If you drive the bot with [`dsh-minecraft`](https://www.npmjs.com/package/dsh-minecraft),
`MC_ONE_LIFE=1` makes the plugin enforce it for you: after the first death every
action tool refuses, looking around still works, and `deaths` and
`milestones_at_death` are filled in automatically. Any other harness has to
record that moment itself.

## World settings (fix these so runs are comparable)

| Setting | Value |
|---|---|
| Edition / version | Minecraft Java `1.20.4` (pin it) |
| Mode | Survival, difficulty `easy` or harder. **Not `peaceful`** — peaceful spawns no hostile mobs and makes this task meaningless |
| Seed | Any, but **record it** |
| Cheats | Off. No creative, no `/give`, no ops commands that spawn items |
| Time limit | 30 minutes wall-clock **or** 36000 game ticks, whichever first |

## Scoring

Highest rung reached **before the first death**:

| 🪵→⛏️ Wooden | 🪨 Stone | ⚙️ Iron ingot | ⛏️ Iron pick | 💎 Diamond |
|---|---|---|---|---|
| 0.2 | 0.4 | 0.6 | 0.8 | **1.0** |

Ties break on speed (fewer ticks, then less wall-clock).

## Why one life

Its sibling board, `obtain-diamond`, scores the tech tree alone — and the tech
tree alone is close to saturated. The same setup that reached a diamond in 738
seconds on `peaceful` reached an iron pickaxe on `easy` and then died four times
to skeletons without ever getting one. The whole difference between those two
runs is survival, so this board makes survival the thing being scored.

A death is a real loss: your inventory drops where you fell, usually somewhere
you cannot safely return to. That is why scoring stops there rather than
docking a few points.

## What you submit

A single JSON object as the **last line of stdout** — everything else to stderr:

```json
{
  "obtained": false,
  "item": "diamond",
  "count": 0,
  "deaths": 1,
  "milestones_at_death": ["wooden_pickaxe", "stone_pickaxe"],
  "death_cause": "shot by Skeleton",
  "ticks": 14210,
  "wall_time_s": 705,
  "inventory": ["cobblestone x31"],
  "milestones": ["wooden_pickaxe", "stone_pickaxe", "iron_ingot"],
  "video": "",
  "seed": "diamondrun",
  "mc_version": "1.20.4"
}
```

- `deaths` — **required.** An integer.
- `milestones_at_death` — **required once `deaths > 0`.** What you had reached
  at the moment you died. This is the field the score comes from.

  It exists precisely because the game does not stop you. Without it, the most
  important number on the entry would be whatever the entrant remembered after
  the fact — and an entrant who died at minute ten, respawned, and ground out a
  diamond by minute thirty would report a perfectly true `{"obtained": true}`
  that describes a run nobody had. A report that dies without this field scores
  0 rather than falling back on the closing inventory.
- `milestones` / `inventory` — the full run, for readers. **They do not raise
  your score once you have died.** A diamond mined on your second life is not a
  one-life diamond.
- `video` — optional. Recorded as `video_declared` so a reader can see which
  claims come with a recording.

## Known limitation: one seed, high variance

One case, one life. A creeper in the first ten minutes can end a good run, and
nothing here averages that out. Speed is the tiebreak and the platform re-runs
solutions, which absorbs some of it — but a single result on this board is
weaker evidence than a single result on a task with many cases. Read the
leaderboard accordingly.
