# Attribution — MMLU

This task vendors a subset of **MMLU** (Massive Multitask Language Understanding).

- **Source (data):** https://huggingface.co/datasets/cais/mmlu
- **Source (original):** https://github.com/hendrycks/test
- **Paper:** Hendrycks et al., "Measuring Massive Multitask Language Understanding" (2021)
- **License:** MIT License
- **What we use:** 25 questions sampled at even offsets across the `test` split
  (for subject diversity), fetched at build time by `build_cases.py` via the
  Hugging Face datasets-server API. Question text, choices, and gold answers are
  reproduced unmodified; we only render the choices as A–D and add an
  output-format instruction.

MIT License notice (reproduced as required):

```
MIT License

Copyright (c) 2020 Dan Hendrycks

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
