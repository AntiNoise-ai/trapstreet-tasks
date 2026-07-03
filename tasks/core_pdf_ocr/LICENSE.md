# Data License & Attribution

## Source text

The text content rendered into each PDF is sampled from **Project Gutenberg** public-domain e-texts. Specifically, one short paragraph each from:

- *Alice's Adventures in Wonderland* — Lewis Carroll (Gutenberg #11)
- *The Adventures of Tom Sawyer* — Mark Twain (Gutenberg #74)
- *The Adventures of Huckleberry Finn* — Mark Twain (Gutenberg #76)
- *Dracula* — Bram Stoker (Gutenberg #345)
- *Pride and Prejudice* — Jane Austen (Gutenberg #1342)

All five works are in the public domain in the United States; Project Gutenberg distributes the text freely (https://www.gutenberg.org).

## PDF rendering

The PDFs were generated synthetically using Pillow (PIL) — each shows a single page rendered from the Gutenberg text in Times New Roman / Georgia at 200dpi, with progressively heavier "scan" artifacts applied per difficulty tier:

- `clean`: no artifacts
- `mild`: light sepia tint + low-frequency noise + 0.8° rotation + JPEG q85
- `moderate`: stronger noise + paper texture + 2.5° rotation + Gaussian blur + JPEG q70
- `heavy`: dirt spots + heavy noise + 5° rotation + heavier blur + JPEG q50

These are SYNTHETIC scan artifacts, not real aged-book scans. A future v2 could pair with real Internet Archive / HathiTrust scans (currently blocked by access restrictions).

## Generator code license

Released under the same license as the trapstreet-tasks repo.

## Why synthetic, not real scans

Original plan was to use real Internet Archive scans paired with Project Gutenberg ground truth. As of June 2026, Internet Archive's "Controlled Digital Lending" restrictions block most book PDF downloads without a logged-in account, making the pairing approach impractical for an OSS eval. Synthetic generation gives us:

1. Controlled difficulty curve (4 tiers)
2. Zero license / access risk
3. Reproducible: anyone can regenerate by running the build script with the same seed
