# Data License & Attribution

## Haystack source: Paul Graham essays

The 38 essays used to construct the haystacks come from **Paul Graham's published essays** at https://paulgraham.com/articles.html. These essays are freely distributed by the author for non-commercial use; they have been mirrored in multiple academic NIAH evaluation projects (including gkamradt's original needle-in-a-haystack test and NVIDIA RULER).

Per the standard convention in NIAH-style evals, the essays are used as **filler text only** — the model is not asked to summarize, attribute, or repeat them; they exist solely to fill the context window. The task does NOT redistribute the essays for their content value.

If Paul Graham objects to this use, the haystack can be regenerated from any other public-domain corpus (e.g. Project Gutenberg, Wikipedia text dumps) without changing the eval structure.

## Pattern inspiration: NVIDIA RULER + gkamradt NIAH

The needle-in-a-haystack pattern is inspired by:

- **gkamradt / LLMTest_NeedleInAHaystack** (MIT) — https://github.com/gkamradt/LLMTest_NeedleInAHaystack
- **NVIDIA RULER** (Apache 2.0) — https://github.com/NVIDIA/RULER

Both define the basic format: a unique fact ("the magic number is X") buried in essay padding, with a question that requires the model to retrieve X. This task uses the same paradigm but with a simpler self-contained generator (no nemo/tokenizer dependency).

## License of THIS task

The generator code + task structure are released under the same license as the trapstreet-tasks repo. Haystack content is the user's responsibility (PG essays are freely-shared, but not formally CC-licensed).

## Citations

```bibtex
@misc{kamradt2023niah,
  title  = {Needle In A Haystack — Pressure Testing LLMs},
  author = {Kamradt, Greg},
  year   = {2023},
  url    = {https://github.com/gkamradt/LLMTest_NeedleInAHaystack},
}

@article{hsieh2024ruler,
  title  = {RULER: What's the Real Context Size of Your Long-Context Language Models?},
  author = {Hsieh, Cheng-Ping and Sun, Simeng and Kriman, Samuel and Acharya, Shantanu and Rekesh, Dima and Jia, Fei and Zhang, Yang and Ginsburg, Boris},
  year   = {2024},
  url    = {https://github.com/NVIDIA/RULER},
}
```
