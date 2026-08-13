# Image License & Attribution

The 20 camera trap images in `inputs/*/document.jpg` are derived from the **Snapshot Serengeti** dataset.

## Source

**Snapshot Serengeti, high-frequency annotated camera trap images of 40 mammalian species in an African savanna**
Swanson, A., Kosmala, M., Lintott, C., Simpson, R., Smith, A., Packer, C. (2015).
Scientific Data 2, 150026.
DOI: https://doi.org/10.5061/dryad.5pt92
Hosted on LILA BC: https://lila.science/datasets/snapshot-serengeti

## License

The original Snapshot Serengeti dataset is released under the **Community Data License Agreement — Permissive 1.0 (CDLA-Permissive-1.0)**:
https://cdla.io/permissive-1-0/

This is a permissive license — sharing and redistribution allowed with attribution.

## What was modified

- **Sampled 20 of 7.1M images** from the full Snapshot Serengeti corpus: 2 images each of 10 distinct species (zebra, wildebeest, buffalo, elephant, giraffe, warthog, lion, leopard, cheetah, hyena).
- **Source events:** drawn from `gold_standard_data.csv` — expert-verified species labels (not crowdsourced consensus), to ensure ground-truth correctness.
- **Resized to ≤1280 px** on the long edge, re-saved as JPEG quality 85 (~77–469 KB each). Originals were 2048×1536 from the camera trap cameras.

No image content was retouched — only downsampling.

## Citation

```bibtex
@article{swanson2015snapshot,
  author  = {Swanson, Alexandra and Kosmala, Margaret and Lintott, Chris and Simpson, Robert and Smith, Arfon and Packer, Craig},
  title   = {Snapshot Serengeti, high-frequency annotated camera trap images of 40 mammalian species in an African savanna},
  journal = {Scientific Data},
  volume  = {2},
  pages   = {150026},
  year    = {2015},
  doi     = {10.1038/sdata.2015.26}
}
```
