# Attribution — pdf_chart_values

- **Document:** *Summary of Economic Projections*, released in conjunction with
  the Federal Open Market Committee meeting of June 16–17, 2026
- **Issuer:** Board of Governors of the Federal Reserve System
- **Obtained from:**
  <https://www.federalreserve.gov/monetarypolicy/files/fomcprojtabl20260617.pdf>
- **Licence:** a work of the United States federal government, not subject to
  copyright in the United States. Freely redistributable, no permission needed,
  no notice required. Attribution is given here as good practice, not as a
  licence condition.

## What was changed, and why it is disclosed

`sep_charts.pdf` is the released SEP with **pages 3–15 — every figure page —
replaced by 200 dpi JPEG images of themselves**. Pages 1, 2, 16 and 17 are
byte-for-byte the original. Nothing is added, removed, reordered or retouched.

The reason is not that images are harder to read. It is that the figures are
drawn as vector paths, and while no parser can read a data point out of a path,
`page.get_drawings()` can measure every bar and dot exactly — the task's own
gold is measured that way. Shipping the vector charts would hand a
geometry-reading solution a perfect score for work the task is not trying to
measure. Rasterising leaves the value where a reader finds it: in pixels.

## Reproducing the document

```bash
curl -O https://www.federalreserve.gov/monetarypolicy/files/fomcprojtabl20260617.pdf
python3 build_document.py fomcprojtabl20260617.pdf sep_charts.pdf
```

`build_document.py` asserts afterwards that no rasterised page carries text or
vector paths.

## A note on the answer key

The Federal Reserve also publishes accessible versions of these figures, which
list the per-bin participant counts as text. That listing was used once, as an
independent check that the measured gold was right — it agrees. It is also a
complete answer key for anyone whose solution goes and fetches it, which is
recorded under Known limitations in [README.md](README.md).
