# Image License & Attribution

The 5 source bloodstain pattern images used in this task (referenced under multiple case IDs) are derived from the **CSAFE Impact Spatter Dataset**, sampled and resized for this eval.

## Source

**A data set of bloodstain patterns for teaching and research in bloodstain pattern analysis: Impact beating spatters**
Attinger, D., Liu, Y., Bybee, T., De Brabanter, K. (2018).
Data in Brief, 18, 648-654.
DOI: https://doi.org/10.1016/j.dib.2018.02.070
Original dataset: 61 controlled-impact bloodstain pattern scans + per-scan experimental metadata.

## License

The original dataset is released under **Creative Commons Attribution 4.0 International (CC BY 4.0)**:
https://creativecommons.org/licenses/by/4.0/

## What was modified

- **Sampled 5 of 61 scans** to give clear physical variety:
  - `C2`: sliding cylinder rig, ~46 cm distance, low velocity, pool source, poster board
  - `C4`: sliding cylinder rig, ~46 cm distance, higher velocity, pool source, poster board
  - `HP_15`: dowel rig, ~193 cm distance, pool source, poster board
  - `HP_50`: dowel rig, ~71 cm distance, **wetted foam source** (not pool)
  - `HP_58`: dowel rig, **butcher paper surface** (not poster board)
- **Resized to ≤1280 px** on the long edge, re-saved as JPEG q85 (~10-110 KB each). The original 600-dpi scans are ~12-50 MB each at 16800×26400 px.

The same image is reused across 4 cases per scan (paired with different hypothetical suspect statements), giving 20 image-statement-verdict triples from 5 unique images.

No image content was retouched — only downsampling.

## Citation

```bibtex
@article{attinger2018bloodstain,
  author = {Attinger, Daniel and Liu, Yu and Bybee, Tushar and De Brabanter, Kris},
  title = {A data set of bloodstain patterns for teaching and research in bloodstain pattern analysis: Impact beating spatters},
  journal = {Data in Brief},
  volume = {18},
  pages = {648--654},
  year = {2018},
  doi = {10.1016/j.dib.2018.02.070}
}
```
