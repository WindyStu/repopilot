# Controlled RepoPilot Evaluation — E2E v2

Dataset: `repopilot-e2e-v2` · Model: `deepseek/deepseek-flash` · 20 paired tasks.

| Metric | Baseline | Enhanced | Enhanced - baseline |
|---|---:|---:|---:|
| Task Success Rate | 4/20 (20.0%) | 9/20 (45.0%) | +25.0 pp |
| Retrieval Recall@5 | N/A | 92.5% | N/A |
| Mean input tokens | 15,321.10 | 24,098.30 | +57.3% |
| Mean strong-model calls | 7.95 | 7.20 | -9.4% |
| Mean active wall seconds | 24.98 | 27.98 | +12.0% |
| Hidden-test pass rate | 36/69 (52.2%) | 44/69 (63.8%) | +11.6 pp |

The frozen set contains 5 authored and 15 real-project tasks, split into 5 easy, 10 medium, and 5 hard tasks. Paired
outcomes: 6 enhanced-only wins, 1 baseline-only win, 3 solved by both, and 10 solved by neither.

Each task has one run per variant. Results are descriptive and do not claim statistical significance. Failed tasks remain
in the denominator; task-level records, trajectories, solution patches, and JUnit evidence are retained in this directory.
