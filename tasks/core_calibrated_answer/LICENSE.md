# Data License & Attribution

## Source

**SimpleQA: Measuring short-form factuality in large language models**
Wei, J., Karina, N., Chung, H. W., Jiao, Y. J., Papay, S., Glaese, A., Schulman, J., Fedus, W. (2024).
OpenAI. Paper: https://cdn.openai.com/papers/simpleqa.pdf
Reference implementation: https://github.com/openai/simple-evals

## License

The SimpleQA dataset + reference code are released under **MIT License**:
https://opensource.org/license/mit

## What was modified

- **Sampled 30 questions** from the 4,326-question SimpleQA test set: ~3 per topic across all 10 topics (Science, Geography, Sports, Art, Politics, Other, TV, Music, History, Video games).
- Reformatted as per-case `question.txt` (question + explicit calibration instructions).
- Extended the trap judge with two new matcher kinds:
  - `calibrated_correctness` — 3-way scoring (CORRECT=1.0, NOT_ATTEMPTED=0.5, INCORRECT=0.0), following SimpleQA's grader taxonomy
  - `no_over_claim` — rejects answers containing over-confident wording ("definitely", "certainly", etc.)
- Also rewired `run_matchers()` to accept 3-tuple matcher returns so partial-credit scoring works cleanly.

## Citation

```bibtex
@article{wei2024simpleqa,
  author  = {Wei, Jason and Karina, Nguyen and Chung, Hyung Won and Jiao, Yunxin Joy and Papay, Spencer and Glaese, Amelia and Schulman, John and Fedus, William},
  title   = {Measuring short-form factuality in large language models},
  journal = {OpenAI},
  year    = {2024}
}
```
