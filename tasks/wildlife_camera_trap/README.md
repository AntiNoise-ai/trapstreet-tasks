# Wildlife Camera Trap — Species ID

A trap-compatible task that tests vision-LLM species identification on real Serengeti camera trap photos. 20 cases, 10 species × 2 images each. Multiple-choice classification.

## What this task tests

**Can a vision model correctly identify African wildlife from camera trap photos?**

This is a real conservation-tech workload: organizations like Snapshot Serengeti, WildCam, and Wildbook process millions of camera trap images annually. Currently they rely on:

1. Citizen scientists (slow, requires recruitment)
2. Specialized vision models (Wildlife Insights, MegaDetector — fast but require ML expertise to deploy)
3. Manual review by ecologists (gold standard, doesn't scale)

A general-purpose vision LLM that can hit 80%+ would let small conservation groups skip building specialized infrastructure. The cost-per-image question is critical because volume is enormous (a single park can generate millions of images/year).

## What's actually in the eval

20 images from Snapshot Serengeti, drawn from the **gold standard** subset (expert-verified, not crowdsourced consensus).

### Species + difficulty breakdown

| Difficulty | Species (2 images each) | Why |
|---|---|---|
| **easy** (10 cases) | zebra, wildebeest, buffalo, elephant, giraffe | Iconic, frequent in any training corpus |
| **medium** (6 cases) | warthog, lion, hyena | Recognisable but more easily confused (lion vs other big cat, hyena vs jackal) |
| **hard** (4 cases) | cheetah, leopard | Often partially visible, distinctive rosettes vs spots distinction is real forensic skill |

The two images per species deliberately span "clear close-up" and "challenging shot" — camera traps frequently capture animals from odd angles, at night, or partially out of frame. This is realistic, not a curated showcase.

## Input

Per case the agent receives:
- `INPUTS["question.txt"]` — multiple-choice prompt with the 10 species options listed
- `INPUTS["document.jpg"]` — the camera trap photo (77–469 KB JPEG, max 1280 px long edge)

## Expected output

A single word on stdout: one of `buffalo`, `cheetah`, `elephant`, `giraffe`, `hyena`, `leopard`, `lion`, `warthog`, `wildebeest`, `zebra`.

The judge enforces:
- **Leading word match** — first alpha token must be one of the 10 species names. Preamble like "I see a leopard" fails.
- **No hedge** — "I cannot determine", "could be either", "the image is unclear", etc. all auto-fail.

Each case scores 1.0 / 0.0. Run passes if ≥80% correct.

## Why this is a meaningful TrapStreet task

1. **Real-world demand exists today** — conservation organizations have this exact workflow
2. **Cost-vs-accuracy is the real question** — at the volume of camera trap deployments, even 1% cost reduction is meaningful
3. **Differentiated difficulty** — easy/medium/hard tiers let the eval reveal which model class is "good enough"
4. **Out-of-distribution check** — most LLMs were trained on web photos, not camera trap photos (lower resolution, night IR mode, watermarks, motion blur)

## Honest limitations

- **Only 10 species.** Snapshot Serengeti has 61 species in its label set; we picked the most distinctive 10 for v1.
- **No "empty" frames.** ~60% of real camera trap frames are empty (false triggers from wind, sun shadows). A real deployment task would include "no animal present" as a class. Skipped for v1 since it's a different test.
- **Single-species frames only.** Real shots can have multiple species (zebra + wildebeest in same frame is common). Filtered to NumSpecies=1 to avoid ambiguity.
- **Serengeti-specific.** Different ecosystems have different species. The 10 picked here are East African savanna fauna. A North American camera trap eval would need different species.
- **No annotation of behavior.** Snapshot Serengeti has rich behavior metadata (standing, resting, eating, moving) that future versions could test.

## Image source & license

All 20 images derive from Snapshot Serengeti (Swanson et al. 2015), CDLA-Permissive-1.0. See [LICENSE.md](LICENSE.md).
