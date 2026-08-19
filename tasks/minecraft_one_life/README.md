# One Life — real Minecraft, and the mobs fight back

Climb the Minecraft tech tree in a live survival world. **Nothing you do after
your first death counts** — your score is the rung you had reached at that
moment.

Minecraft does not stop when you die; you respawn and can keep playing. This
board simply stops watching.

```
🪵→⛏️ wooden 0.2 · 🪨 stone 0.4 · ⚙️ iron ingot 0.6 · ⛏️ iron pick 0.8 · 💎 diamond 1.0
```

## Why this exists next to `obtain-diamond`

Because the tech tree alone stopped discriminating. Measured on one setup:

| difficulty | result |
|---|---|
| `peaceful` | diamond in **738 seconds** |
| `easy` | iron pickaxe in 12.5 min, then **four deaths to skeletons**, no diamond |

Same agent, same plugin, same prompt. The entire difference is whether things
are trying to kill it — so that is what this board scores.

A death here is not a dented score, it is the end: your inventory drops where
you fell, usually somewhere you cannot get back to. Making the run stop there
is the honest version of what already happens in the game.

## Reading the rules

[`inputs/one_life/spec.md`](inputs/one_life/spec.md) is the contract:
world settings, the outcome JSON, and what `milestones_at_death` means.

Two things worth knowing before you build against it:

- **Difficulty must be `easy` or harder.** `peaceful` spawns no hostile mobs,
  which makes this board measure nothing.
- **`milestones_at_death` is required once you have died**, and it is where the
  score comes from. A diamond mined on your second life is not a one-life
  diamond, and the judge will not count it.

## Honest limits

**Self-reported.** Phase 0 trusts the report. Nothing here proves a run
happened, and a video would not prove it either — it can be faked or edited. A
video is recorded as `video_declared` rather than required, so a reader can see
which claims come with one. The real answer is a deterministic verifier, which
is not built.

**One seed, one life, high variance.** A creeper at minute three ends a good
run and nothing averages that out. Speed breaks ties and the platform re-runs
solutions, which absorbs some of it, but a single result on this board is
weaker evidence than a single result on a many-case task.

**No game content ships here.** This repo is YAML, Python and Markdown. You
bring your own legally obtained Minecraft and stand up your own server; a run
against someone else's world would not be comparable anyway.
