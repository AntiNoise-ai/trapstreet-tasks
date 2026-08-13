# Data License & Attribution

## Source

**Test of Time (ToT): Benchmarking the Temporal Reasoning Abilities of LLMs**
Bahare Fatemi, Mehran Kazemi, Anton Tsitsulin, Karishma Malkan, Jinyeong Yim, John Palowitch, Sungyong Seo, Jinyoung Sung, Bryan Perozzi (Google DeepMind, 2024).
arXiv: https://arxiv.org/abs/2406.09170
HuggingFace dataset: https://huggingface.co/datasets/baharef/ToT

## License

The original ToT dataset is released under **Creative Commons Attribution 4.0 International (CC BY 4.0)**:
https://creativecommons.org/licenses/by/4.0/

Attribution required. Redistribution allowed.

## What was modified

- **Sampled 21 cases** (3 per question type × 7 types) from the `tot_arithmetic` split (1,850 rows total).
- Per-question-type breakdown: `add_subtract`, `compare`, `multi_op`, `schedule`, `trick`, `duration`, `timezone`.
- Reformatted the gold answers — the original `label` field is a Python dict repr; this task extracts the `answer` / `date` / `time` value and pairs it with appropriate trap matchers (`numeric` for pure-number answers, `keywords_all` for string-based answers, multi-value `keywords_all` for compound answers).

## Citation

```bibtex
@inproceedings{fatemi2024test,
  author = {Bahare Fatemi and Mehran Kazemi and Anton Tsitsulin and Karishma Malkan and Jinyeong Yim and John Palowitch and Sungyong Seo and Jinyoung Sung and Bryan Perozzi},
  title = {Test of Time: A Benchmark for Evaluating LLMs on Temporal Reasoning},
  booktitle = {ICLR},
  year = {2025}
}
```
