# Evaluation protocol

Compare `baseline` and `enhanced` on exactly the same task IDs, Gemini endpoint, temperature/settings, repair budget, Docker
image, and test commands. The baseline disables retrieval and local analysis; enhanced enables deterministic hybrid
retrieval, while a third optional variant enables Qwen analysis/reranking.

Each raw task record contains task ID, variant, success, test status, expected and retrieved files, strong-model calls,
input tokens when the provider reports them, wall time, failure class, and trajectory path. `compare_variants` refuses to
compare different task-ID sets. Failed and skipped tasks remain in the denominator.

Report these metrics:

- task success rate and test pass rate;
- retrieval Recall@5 (only for tasks with labeled relevant files);
- total/mean strong-model calls and input tokens;
- wall time and failure-class counts;
- raw task-level outcomes, not only aggregates.

The repository currently contains deterministic harness tests, not a completed live-model scorecard. Run and commit the
controlled benchmark only after Docker integration and a rotated Gemini key are available. Until then, resume bullets must
describe implemented capabilities rather than unmeasured percentage improvements.

## Current checked-in result

`repopilot-retrieval-v1` labels 20 issue queries against expected RepoPilot source files. The empty-context baseline has
0% Recall@5 and deterministic hybrid retrieval has 90% Recall@5 (18/20 tasks fully recalled). The two misses remain in the
raw report. This benchmark isolates retrieval quality; it does not measure patch correctness or claim a 90% solve rate.

The live Gemini scorecard remains pending because the current WSL network cannot establish TCP 443 to
`generativelanguage.googleapis.com`. Docker integration and credential isolation have been validated independently.
