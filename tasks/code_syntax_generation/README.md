# code_syntax_generation — Does the Model Write Working Python Code?

An open-source evaluation task for **basic code generation** — given a function signature and docstring, can the model produce a complete, correct implementation that passes unit tests?

Useful as a basic sanity check when building AI agents that generate code (code assistants, debugging agents, script generators, refactoring bots).

20 problems sampled from OpenAI's HumanEval benchmark.

## What this task tests

**Given a function signature and docstring describing intended behavior, can the model write a correct implementation?**

Code generation is table-stakes for any code-related agent. The specific failure modes this exposes:

1. **Syntax errors** — code doesn't parse
2. **Logic errors** — code parses and runs but produces wrong output
3. **Edge case failures** — handles the common case but breaks on empty inputs, negatives, or boundary conditions
4. **Import / dependency issues** — model uses a library not imported in the prompt
5. **Type errors** — returns wrong type (e.g., int when str expected)

Every unit test is deterministic and comes from HumanEval's canonical test suite. A model that "looks correct" but fails on an edge case fails the test — no partial credit.

## Case structure

| Difficulty | Cases | Solution length | What it tests |
|---|---|---|---|
| **easy** | 6 | 1-3 lines | Simple transformations (uppercase counting, string reversal, area formula) |
| **medium** | 8 | 4-8 lines | Nontrivial logic (median, sorting subsets, matrix search, common elements) |
| **hard** | 6 | 10+ lines | Multi-step algorithms (nth prime-fib, dict validation, palindrome+even/odd counting) |

Difficulty is proxied by canonical solution length. Real difficulty varies within tier — some short problems have subtle edge cases.

## Input

Per case:
- `INPUTS["question.txt"]` — the HumanEval prompt (function signature + docstring), wrapped with "Return ONLY the complete function definition, no explanation, no markdown fences."

## Expected output

A complete Python function definition matching the signature.

The judge enforces:
- `python_unit_test` — runs the canonical HumanEval test in a subprocess with 10s timeout. All assertions must pass.
- `no_hedge` — rejects "I can't help with that" responses.

Each case scores 1.0 / 0.0. Run passes if ≥80% pass.

## How the judge runs the code

1. Strips ` ```python fences ` if present
2. If model returned function body only (no `def`), prepends the original prompt
3. Composes: `{code}\n\n{test_code}\n\ncheck({entry_point})`
4. Runs in subprocess with 10s timeout
5. Exit 0 = pass; any exception, assertion failure, or timeout = fail

Model code runs in a subprocess but is NOT sandboxed. This is safe for HumanEval (models are given innocuous math/string problems and don't spontaneously write malicious code) but this task should NOT be repurposed to run untrusted arbitrary code.

## Cost

20 problems with short input (function signature + docstring). Output is 5-30 lines of code. Full run: ~$0.05-0.30 on most models.

## Honest limitations

- **Python only.** No JavaScript, TypeScript, Java, Go, Rust, etc. Code agents in production often work across languages — a multi-language variant is a v2.
- **Function-scoped.** All problems are single-function. Real code work involves multi-file changes, imports, class hierarchies. HumanEval is a starting point.
- **Contamination risk.** HumanEval is one of the most-cited coding benchmarks. Every major model has seen it in training. Scores here likely inflated vs. novel problems.
- **Deterministic tests only.** Some real coding tasks have multiple correct implementations that HumanEval-style tests can't validate (e.g., "write a sort function that's stable" — the test just checks correctness, not stability).
- **No test for code style / readability.** Only functional correctness.

## Data source & license

20 problems sampled from OpenAI's HumanEval (`openai/openai_humaneval` on HuggingFace, MIT). See [LICENSE.md](LICENSE.md).
