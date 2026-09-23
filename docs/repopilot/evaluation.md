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

The canonical end-to-end result is `repopilot-e2e-v2`: one baseline and one enhanced DeepSeek Flash run for each of 20
tasks (40 sessions total). The frozen set contains 5 authored tasks and 15 immutable real-project snapshots, with 5 easy,
10 medium, and 5 hard tasks. All tasks passed two-run Docker qualification before the paid experiment.

| Metric | Baseline | Enhanced | Delta |
|---|---:|---:|---:|
| Task Success Rate | 4/20 (20.0%) | 9/20 (45.0%) | +25.0 pp |
| Hidden-test case pass rate | 36/69 (52.2%) | 44/69 (63.8%) | +11.6 pp |
| Retrieval Recall@5 | N/A | 92.5% | N/A |
| Mean input tokens | 15,321.10 | 24,098.30 | +57.3% |
| Mean strong-model calls | 7.95 | 7.20 | -9.4% |
| Mean active wall time | 24.98 s | 27.98 s | +12.0% |

The paired outcomes were 6 enhanced-only wins, 1 baseline-only win, 3 tasks solved by both, and 10 solved by neither.
Enhanced success was 4/5 on authored and 5/15 on real-project tasks, versus 2/5 and 2/15 for baseline. Failure classes and
unsuccessful tasks remain in the report rather than being filtered out. Raw evidence is checked in under
`benchmarks/results/e2e-v2-deepseek-flash-20task/`.

This is a single run per task, so the result is descriptive and does not establish statistical significance. It shows a
higher observed solve rate and fewer strong-model calls, with the explicit trade-off of more input context and active time.
The earlier 3-task `repopilot-e2e-v1` pilot remains under
`benchmarks/results/e2e-v1-deepseek-flash-r2/` and is excluded from the v2 aggregate.

## Retrieval-only smoke result

`repopilot-retrieval-v1` labels 20 issue queries against expected RepoPilot source files. The empty-context baseline has
0% Recall@5 and deterministic hybrid retrieval has 90% Recall@5 (18/20 tasks fully recalled). The two misses remain in the
raw report. This benchmark isolates retrieval quality; it does not measure patch correctness or claim a 90% solve rate.

An earlier pilot replicate is excluded from the primary aggregate because SGLang inherited VPN proxy variables and killed
itself when its localhost warmup was proxied. The harness now bypasses proxies for loopback requests, gates paid evaluation
on a real structured Qwen generation, and marks any fallback enhanced run ineligible rather than silently counting it.
