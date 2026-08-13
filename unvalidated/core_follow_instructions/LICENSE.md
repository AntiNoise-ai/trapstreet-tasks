# Data License & Attribution

## Source: IFEval

**IFEval — Instruction-Following Evaluation for Large Language Models**
Zhou, J., Lu, T., Mishra, S., Brahma, S., Basu, S., Luan, Y., Zhou, D., Hou, L. (2023).
Google. Paper: https://arxiv.org/abs/2311.07911
HuggingFace: https://huggingface.co/datasets/HuggingFaceH4/ifeval

## License

IFEval dataset is released under **Apache 2.0 License**:
https://www.apache.org/licenses/LICENSE-2.0

## What was modified

- **Sampled 25 prompts** from the 541-prompt IFEval train set: 5 single-constraint (easy) + 12 two-constraint (medium) + 8 three-constraint (hard).
- Filtered to cases using only the 20 constraint types supported by our verifier implementation (see `judge.py`).
- Reformatted each case's constraint list into a `matchers` block in `answer.json` for the trap judge.

## Verifier implementation

The constraint verifiers in `judge.py` are re-implemented directly (not imported from Google's IFEval library) to keep the task self-contained. The behavior is designed to match Google's reference verifiers for the supported constraint types.

## Citation

```bibtex
@article{zhou2023ifeval,
  author  = {Zhou, Jeffrey and Lu, Tianjian and Mishra, Swaroop and Brahma, Siddhartha and Basu, Sujoy and Luan, Yi and Zhou, Denny and Hou, Le},
  title   = {Instruction-Following Evaluation for Large Language Models},
  journal = {arXiv preprint arXiv:2311.07911},
  year    = {2023}
}
```
