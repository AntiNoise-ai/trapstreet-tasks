# Data License & Attribution

## Source: LongMemEval

**LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory**
Xiao, W., Huang, Z., Gan, L., He, W., Li, H., Yu, Z., Jiang, H., Wu, F., Zhu, L. (2024).
Paper: https://arxiv.org/abs/2410.10813
Original repo: https://github.com/xiaowu0162/LongMemEval

## License

LongMemEval is released under **MIT License**:
https://opensource.org/license/mit

The processed version used here (`LIXINYI33/longmemeval-s` on HuggingFace) inherits the same license.

## What was modified

- **Sampled 20 conversations** from the 1000-conversation LongMemEval-S dataset (via `LIXINYI33/longmemeval-s`).
- Filtered to cases with 2-6 sessions and short (≤80 char) answers — sizes manageable for typical eval runs (~5-16k tokens per case).
- Distribution: 8 multi-session + 7 temporal-reasoning + 5 knowledge-update.
- Formatted each conversation as a readable "Session N — <date>" structured document + user/assistant turns.
- Extracted answer keywords programmatically for `keywords_all` matcher (up to 3 tokens per case, first sentence only, stopwords excluded).

## Citation

```bibtex
@article{xiao2024longmemeval,
  author  = {Xiao, Wenyue and Huang, Zhiyu and Gan, Lu and He, Wenbo and Li, Han and Yu, Zhaoyang and Jiang, Haitao and Wu, Fei and Zhu, Liang},
  title   = {LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory},
  journal = {arXiv preprint arXiv:2410.10813},
  year    = {2024}
}
```
