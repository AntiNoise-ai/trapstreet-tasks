# Data License & Attribution

## Source: HumanEval

**Evaluating Large Language Models Trained on Code**
Chen, M., Tworek, J., Jun, H., Yuan, Q., Pinto, H. P. O., Kaplan, J., ... Zaremba, W. (2021).
OpenAI. Paper: https://arxiv.org/abs/2107.03374
HuggingFace: https://huggingface.co/datasets/openai/openai_humaneval

## License

HumanEval is released under **MIT License**:
https://opensource.org/license/mit

## What was modified

- **Sampled 20 problems** from the 164-problem HumanEval test set: 6 easy + 8 medium + 6 hard.
- Difficulty is proxied by canonical solution length (shorter = easier, on average).
- Wrapped each prompt with a directive: "Return ONLY the complete function definition, no explanation, no markdown fences" — to focus grading on code, not commentary.
- Ported the canonical test suite into the trap judge as a `python_unit_test` matcher that runs the test in a subprocess with 10s timeout.

## Contamination note

HumanEval is one of the most-cited coding benchmarks and has almost certainly been included in the training data of every major LLM. Scores on this task should be interpreted as a floor ("does the model handle these well-known patterns"), not as a novel test of code generation capability. For more contamination-resistant coding evals, see LiveCodeBench, BigCodeBench, or SWE-Bench.

## Citation

```bibtex
@article{chen2021evaluating,
  author  = {Chen, Mark and Tworek, Jerry and Jun, Heewoo and Yuan, Qiming and Pinto, Henrique Ponde de Oliveira and Kaplan, Jared and Edwards, Harri and Burda, Yuri and Joseph, Nicholas and Brockman, Greg and others},
  title   = {Evaluating Large Language Models Trained on Code},
  journal = {arXiv preprint arXiv:2107.03374},
  year    = {2021}
}
```
