# Data License & Attribution

## Source: Berkeley Function Calling Leaderboard (BFCL)

**Berkeley Function Calling Leaderboard (BFCL)**
Patil, S. G., Zhang, T., Wang, X., Gonzalez, J. E. (2024).
UC Berkeley Sky Computing Lab.
Leaderboard: https://gorilla.cs.berkeley.edu/leaderboard.html
GitHub: https://github.com/ShishirPatil/gorilla

## License

BFCL is released under **Apache 2.0 License**:
https://www.apache.org/licenses/LICENSE-2.0

The processed version used here (`hjshah/bfcl_non_live_parallel` on HuggingFace) inherits the same license.

## What was modified

- **Sampled 20 cases** from BFCL's `parallel` non-live subset (400 total cases): 6 short (2 calls) + 8 medium (3 calls) + 6 long (4 calls).
- Extracted the tool schemas from the embedded system prompt for cleaner presentation.
- Reformatted each case to the trap task format: `question.txt` (with tools + user request) + `answer.json` (with ground truth calls + matchers).
- Implemented a custom `parallel_tool_calls` matcher that parses agent JSON output and compares against the ground truth accepting the multiple valid values per arg (per BFCL's convention).

## Citation

```bibtex
@misc{berkeley-function-calling-leaderboard,
  title  = {Berkeley Function Calling Leaderboard},
  author = {Fanjia Yan and Huanzhi Mao and Charlie Cheng-Jie Ji and Tianjun Zhang and Shishir G. Patil and Ion Stoica and Joseph E. Gonzalez},
  howpublished = {\url{https://gorilla.cs.berkeley.edu/blogs/8_berkeley_function_calling_leaderboard.html}},
  year = {2024},
}
```
