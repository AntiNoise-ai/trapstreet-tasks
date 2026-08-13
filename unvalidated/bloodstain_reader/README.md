# Bloodstain Reader — Evidence vs Suspect Statement Eval

A trap-compatible task that tests whether a vision-LLM can do real forensic reasoning: given a bloodstain pattern (physical evidence) and a hypothetical suspect statement, judge whether the evidence **supports**, **contradicts**, or **fails to support** the statement.

20 cases drawn from 5 distinct CSAFE bloodstain scans (real lab data), each paired with 4 hypothetical statements.

## What this task tests

**Can the model use physical evidence to constrain a narrative?**

This is the core skill of crime scene reconstruction: matching what the evidence shows against what a suspect claims happened. Each case forces a three-way commit:

- **supports** — the visible evidence is consistent with the statement
- **contradicts** — the visible evidence is inconsistent with the statement
- **fails to support** — the statement makes a claim the physical evidence cannot speak to (timing, motive, relationships, post-event actions)

The "fails to support" verdict is critical. Many models will default to supports/contradicts even when the evidence is silent. Recognising when physical evidence cannot adjudicate a claim is real forensic literacy.

## Why bloodstain patterns work for this

Each scan in the source dataset (CSAFE 2018) was created in a controlled rig with measured parameters: source-to-target distance, impact velocity, surface material, source type (blood pool vs blood-soaked foam). That means we **know the ground truth** for each scan — and we can design statements that interact predictably with those physical parameters.

Example for scan `C2` (close range, low velocity, single dense low cluster):

| Statement | Verdict | Why |
|---|---|---|
| "I hit them once with my fist while we were standing close together." | **supports** | Single low cluster matches one close-range impact |
| "We were standing on opposite sides of the room — about 5 meters apart." | **contradicts** | 5 m would scatter droplets widely; visible pattern is concentrated |
| "I struck them multiple times at different places — at least 4 or 5 blows." | **contradicts** | Only one cluster visible; multiple impacts would produce multiple clusters |
| "The argument before this lasted about 30 minutes." | **fails to support** | Time of preceding events isn't encoded in spatter physics |

## Visual features the model must interpret

Across the 5 source scans:

| Feature | Scans | What it reveals |
|---|---|---|
| **Droplet density** (dense vs sparse) | C2 dense, HP_15 sparse | Distance + impact force |
| **Spread area** (concentrated vs wide) | C2 concentrated, C4 wide | Velocity / energy of impact |
| **Droplet size** (small vs large) | C-series small, HP-series larger | Velocity |
| **Directional tails on droplets** | HP_50 has them; others don't | Foam-source spray vs pool impact |
| **Background colour/texture** | HP_58 is cream paper; others bright white | Surface material (butcher paper vs poster board) |
| **Pattern shape** (horizontal band vs vertical cluster) | C2 horizontal-low, HP_58 vertical-upper | Geometry of impact |

A model that gets ≥80% across this task is doing something close to junior-level BPA reasoning. A model that scores near random is treating the image as a yes/no "is there blood?" classifier.

## Input

Per case:
- `INPUTS["question.txt"]` — the statement + the supports/contradicts/fails prompt
- `INPUTS["document.jpg"]` — the bloodstain pattern photo (10-110 KB, max 1280 px long edge)

## Expected output

A single word on stdout: `supports`, `contradicts`, or `fails`. Plain text or `{"answer":"..."}` JSON.

The judge enforces:
- **Leading word must match** — first alpha token (after stripping `Answer:` prefixes) must be `supports`, `contradicts`, or `fails`. Hedging or multi-sentence preamble fails the leading-word matcher.
- **No hedge phrases** — "I cannot determine", "as an AI", "insufficient information", etc. all auto-fail.

Each case scores 1.0 (pass) or 0.0 (fail). Run passes if ≥80% of cases pass.

## Verdict distribution

| Verdict | Cases |
|---|---|
| `supports` | 5 |
| `contradicts` | 10 |
| `fails_to_support` | 5 |

The skew toward `contradicts` reflects realistic forensic scenarios: suspects often make claims the physical evidence will disprove. Each scan contributes 1 supports + 2 contradicts + 1 fails.

## Image source & license

All 5 images derive from the CSAFE Impact Spatter Dataset (Attinger et al. 2018, [DOI](https://doi.org/10.1016/j.dib.2018.02.070)), CC BY 4.0. See [LICENSE.md](LICENSE.md).

## Important: scope and limitations

- This task only uses **impact beating** patterns. Gunshot, cast-off, transfer, and passive drip patterns are NOT represented — don't read into this task more than it tests.
- The 5 source scans are from controlled lab conditions. Real crime scene spatter is messier (mixed mechanisms, irregular surfaces, lighting noise).
- The verdicts are designed to be defensible against the physical metadata, NOT against deep BPA expertise. A trained Bloodstain Pattern Analyst might disagree on edge cases.
- This eval does NOT replace expert BPA software (HemoSpat, BackTrack) which use precise geometric reconstruction. It tests whether a general-purpose vision LLM can do qualitative evidence-narrative reasoning at all.
