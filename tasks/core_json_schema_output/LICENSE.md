# Data License & Attribution

The 20 cases in this task are sampled from the **Berkeley Function Calling Leaderboard (BFCL)** v4 `simple_python` split.

## Source

**Berkeley Function Calling Leaderboard / Gorilla**
Patil, S. G. et al., UC Berkeley.
GitHub: https://github.com/ShishirPatil/gorilla
BFCL data path: `gorilla/berkeley-function-call-leaderboard/bfcl_eval/data/BFCL_v4_simple_python.json` (+ matching `possible_answer/`)

## License

The original BFCL dataset is released under **Apache License 2.0**:
https://www.apache.org/licenses/LICENSE-2.0

Redistribution allowed with attribution preserved.

## What was modified

- **Sampled 20 cases** from the 400-case `BFCL_v4_simple_python` split: 10 cases where every gold arg has a single accepted value (strictest), 10 with multi-value accepted golds (test optional/default handling).
- Reformatted as per-case `inputs/<id>/question.txt` (prompt + schema embedded) + `expected/<id>/answer.json` (gold function call + custom `json_call` matcher spec).
- Did NOT modify the function specs, user requests, or gold answers themselves.

## Citation

```bibtex
@inproceedings{patil2024gorilla,
  author = {Shishir G. Patil and Tianjun Zhang and Xin Wang and Joseph E. Gonzalez},
  title = {Gorilla: Large Language Model Connected with Massive APIs},
  booktitle = {NeurIPS},
  year = {2024}
}
```
