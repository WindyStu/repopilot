# Evaluation protocol

Compare `baseline` and `enhanced` on exactly the same task IDs, DeepSeek endpoint, temperature/settings, repair budget, Docker
image, and test commands. The baseline disables retrieval and local analysis; enhanced enables deterministic hybrid
retrieval plus Qwen analysis.

Each raw task record contains task ID, variant, success, test status, expected and retrieved files, strong-model calls,
input tokens when the provider reports them, wall time, failure class, and trajectory path. `compare_variants` refuses to
compare different task-ID sets. Failed and skipped tasks remain in the denominator.

Report these metrics:

- task success rate and test pass rate;
- retrieval Recall@5 (only for tasks with labeled relevant files);
- total/mean strong-model calls and input tokens;
- wall time and failure-class counts;
- raw task-level outcomes, not only aggregates.

The canonical end-to-end result is `repopilot-e2e-v1` with DeepSeek Flash and one run for each of 3 paired tasks. Both
variants solved 3/3 tasks and passed 9/9 hidden tests. Enhanced retrieval reached 100% Recall@5, reduced mean input tokens
from 6,320.33 to 5,847.33 (7.5%), and reduced mean strong-model calls from 5.67 to 5.00 (11.8%). Mean active wall time
increased from 8.42 to 9.04 seconds (7.4%) because local analysis adds latency. These are descriptive pilot results and do
not establish statistical significance or a solve-rate improvement. Raw evidence is checked in under
`benchmarks/results/e2e-v1-deepseek-flash-r2/`.

## Current checked-in result

`repopilot-retrieval-v1` labels 20 issue queries against expected RepoPilot source files. The empty-context baseline has
0% Recall@5 and deterministic hybrid retrieval has 90% Recall@5 (18/20 tasks fully recalled). The two misses remain in the
raw report. This benchmark isolates retrieval quality; it does not measure patch correctness or claim a 90% solve rate.

An earlier pilot replicate is excluded from the primary aggregate because SGLang inherited VPN proxy variables and killed
itself when its localhost warmup was proxied. The harness now bypasses proxies for loopback requests, gates paid evaluation
on a real structured Qwen generation, and marks any fallback enhanced run ineligible rather than silently counting it.
