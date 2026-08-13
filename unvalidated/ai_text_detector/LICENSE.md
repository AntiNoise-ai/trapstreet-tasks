# Data License & Attribution

The 20 text samples in `inputs/*/document.txt` are derived from the **RAID** dataset (Robust AI Detector benchmark).

## Source

**RAID: A Shared Benchmark for Robust Evaluation of Machine-Generated Text Detectors**
Liam Dugan, Alyssa Hwang, Filip Trhlik, Josh Magnus Ludan, Andrew Zhu, Hainiu Xu, Daphne Ippolito, Chris Callison-Burch (2024).
ACL 2024.
arXiv: https://arxiv.org/abs/2405.07940
HuggingFace dataset: https://huggingface.co/datasets/liamdugan/raid

## License

The original RAID dataset is released under the **MIT License**:
https://opensource.org/license/mit

## What was modified

- **Sampled 20 of ~8M rows** from the `train` split: 10 human-written + 10 AI-generated (2 each from 5 models: chatgpt, gpt4, llama-chat, mistral-chat, cohere-chat).
- **Filtered to:** `attack="none"` (no adversarial perturbations) and text length 800–2000 characters (1–3 paragraphs — enough signal, cheap to run).
- **Domain mix:** abstracts, books, news, recipes, reddit, reviews, wiki — all English.
- Removed metadata fields (`adv_source_id`, `attack`) from the per-case answer.json since they're constant in the sampled subset.

No text content was edited.

## Citation

```bibtex
@inproceedings{dugan2024raid,
  author = {Dugan, Liam and Hwang, Alyssa and Trhlik, Filip and Ludan, Josh Magnus and Zhu, Andrew and Xu, Hainiu and Ippolito, Daphne and Callison-Burch, Chris},
  title = {RAID: A Shared Benchmark for Robust Evaluation of Machine-Generated Text Detectors},
  booktitle = {ACL},
  year = {2024}
}
```
