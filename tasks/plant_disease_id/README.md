# Plant Disease ID — Healthy or Diseased?

A trap-compatible task that tests vision-LLM plant pathology identification on PlantVillage leaf photos. 20 cases, 6-way multiple choice.

## What this task tests

**Can a vision model correctly diagnose a plant leaf disease?**

This is a real agritech workload. Apps like Plantix and PlantNet process millions of farmer-submitted photos to triage crop diseases. Smallholder farmers in Africa, South Asia, and Latin America often have no access to extension officers — a phone snap + AI verdict is the only screening they get. Accuracy at scale, at low cost-per-image, matters.

The PlantVillage dataset is the canonical benchmark for this category. It's been used in 1000+ ML papers since 2016. Classical CNNs reach 99%+ on it, so the question isn't "can vision LLMs match CNNs" — it's "can they do useful zero-shot classification without fine-tuning, at what cost?"

## What's actually in the eval

20 leaf images, 10 classes (5 crops × 2 conditions each):

| Crop | Healthy | Disease |
|---|---|---|
| Apple | 2 images | Cedar apple rust (2) |
| Corn (maize) | 2 images | Common rust (2) |
| Tomato | 2 images | Early blight (2) |
| Potato | 2 images | Late blight (2) |
| Grape | 2 images | Black rot (2) |

### Difficulty tiers

| Difficulty | Cases | Why |
|---|---|---|
| **easy** (14) | All 10 healthy + 2 common rust + 2 cedar apple rust | Healthy is visually uniform; rust diseases have distinctive orange/brown pustules |
| **medium** (4) | 2 early blight + 2 late blight | Both produce dark spots — easy to confuse with each other |
| **hard** (2) | 2 black rot | Small dark spots can blend with leaf shadows / texture |

The model must distinguish among 6 conditions: `healthy`, `cedar apple rust`, `common rust`, `early blight`, `late blight`, `black rot`.

## Input

Per case the agent receives:
- `INPUTS["question.txt"]` — multiple-choice prompt listing the 6 conditions
- `INPUTS["document.jpg"]` — the leaf photo (~8–27 KB JPEG, 256×256)

## Expected output

A condition phrase on stdout: one of `healthy`, `cedar apple rust`, `common rust`, `early blight`, `late blight`, `black rot`.

The judge enforces:
- **Leading word match** — first alpha token must be the discriminating word (`cedar`, `common`, `early`, `late`, `black`, or `healthy`)
- **Keyword presence** (multi-word answers) — second word must appear in the answer
- **No hedge** — auto-fail on "I cannot tell from the image" etc.

Each case scores 1.0 / 0.0. Run passes if ≥80% correct.

## Why this is a meaningful TrapStreet task

1. **PlantVillage is the de facto baseline** — every plant disease AI paper benchmarks on it. A new TrapStreet entry slots in next to existing literature.
2. **Cheap-vs-expensive comparison is critical at agritech scale** — even 1¢ per image savings matters at the volume of farmer-app submissions.
3. **Vision LLMs vs specialized CNNs** — this task lets us see how close zero-shot vision LLMs are to dedicated classifiers like AlexNet/ResNet trained on PlantVillage.
4. **6-way classification > binary** — more discriminating than just "healthy or not"; lets the eval expose models that pass at "is something wrong?" but fail at "what is wrong?"

## Honest limitations

- **Studio-style photos.** PlantVillage images are single leaves on a uniform grey background. Real-world farmer photos are in-the-wild (multi-leaf, varied lighting, soil/weeds visible). Models that score 100% here may drop to ~50% on PlantDoc (in-the-wild dataset). v2 could add PlantDoc samples.
- **Only 5 crops + 5 diseases.** PlantVillage has 14 crops × 26 diseases (38 classes total). We picked the most globally relevant subset for v1.
- **Disease severity is one image.** Real diagnosis often needs multiple shots (different leaves, different stages). Each case here is a single isolated leaf.
- **No "non-leaf" or "unknown" class.** Real apps need to detect "this isn't a leaf" or "unknown disease."

## Image source & license

All 20 images derive from PlantVillage (Mohanty et al. 2016), CC BY-SA 3.0. See [LICENSE.md](LICENSE.md).
