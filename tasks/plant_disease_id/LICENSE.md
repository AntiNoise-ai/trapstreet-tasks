# Image License & Attribution

The 20 plant leaf images in `inputs/*/document.jpg` are derived from the **PlantVillage dataset**.

## Source

**Using Deep Learning for Image-Based Plant Disease Detection**
Mohanty, Sharada P., David P. Hughes, and Marcel Salathé (2016).
Frontiers in Plant Science 7, 1419.
DOI: https://doi.org/10.3389/fpls.2016.01419
Original dataset: https://github.com/spMohanty/PlantVillage-Dataset (54,306 images, 38 classes)
HuggingFace mirror used: https://huggingface.co/datasets/BrandonFors/Plant-Diseases-PlantVillage-Dataset

## License

The original PlantVillage dataset (Mohanty et al.) is licensed under **Creative Commons Attribution-ShareAlike 3.0 Unported (CC BY-SA 3.0)**:
https://creativecommons.org/licenses/by-sa/3.0/

Attribution required. Derivative works (such as this eval task) must be released under the same or compatible license.

## What was modified

- **Sampled 20 of 54,306 images**: 2 each of 10 classes covering 5 crop × condition pairs:
  - Apple — healthy + Cedar apple rust
  - Corn (maize) — healthy + Common rust
  - Tomato — healthy + Early blight
  - Potato — healthy + Late blight
  - Grape — healthy + Black rot
- Originals are 256×256 — no resizing needed. Saved as JPEG quality 85 (~8–27 KB each).
- No image content was edited.

## Citation

```bibtex
@article{mohanty2016plantvillage,
  author  = {Mohanty, Sharada P. and Hughes, David P. and Salath{\'e}, Marcel},
  title   = {Using Deep Learning for Image-Based Plant Disease Detection},
  journal = {Frontiers in Plant Science},
  volume  = {7},
  pages   = {1419},
  year    = {2016},
  doi     = {10.3389/fpls.2016.01419}
}
```
