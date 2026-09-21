# 10–20 minute interview narrative

## 1. Problem and baseline (2 minutes)

mini-swe-agent is intentionally a minimal shell loop. That makes a clean baseline, but the strong model must repeatedly
discover repository structure and can spend context on irrelevant files. RepoPilot keeps that loop and adds an observable
retrieval layer instead of replacing the upstream agent.

## 2. Retrieval design (4 minutes)

The indexer uses Python `ast`, records symbol spans/imports/hashes, follows ignore rules, and rejects escaping symlinks.
Retrieval combines BM25, exact identifier/path evidence, and one-hop dependency expansion. The context packer selects whole
symbols under a fixed character budget and records why every excerpt was included.

## 3. Model routing (3 minutes)

Qwen3-0.6B runs locally through SGLang and only performs bounded structured tasks. Invalid JSON, timeout, or downtime falls
back to deterministic extraction. Gemini 3.8 Flash performs the harder diagnosis and patching through the existing
mini-swe-agent tool-call abstraction. Keys remain process environment only.

## 4. Safety and recovery (3 minutes)

The CLI copies and filters the repository before execution. Generated commands run in a non-root, no-network Docker
container with resource/time/output limits and no credentials. Failed tests are summarized into the next attempt, with a
small explicit retry budget; the last patch and every trajectory are retained on exhaustion.

## 5. Evaluation and demo (3–6 minutes)

Show one fixture issue, retrieved files/evidence, the first failed test, repair feedback, final patch, and passing tests.
Then compare the same task set under baseline and enhanced modes. Be explicit that Recall@5 measures retrieval, while task
success measures the whole system. Close with limitations: Python-only indexing, prebuilt offline runner dependencies, free
API quotas, and the small benchmark's uncertainty.

## Resume wording before live benchmark

“Extended mini-swe-agent with explainable Python code retrieval, local Qwen3-0.6B routing, credential-isolated Docker
execution, bounded test-driven repair, and reproducible baseline comparison; achieved 90% Recall@5 versus a 0% no-context
baseline on a checked-in 20-task retrieval benchmark.”

Always call this a retrieval benchmark. Do not describe it as a bug-fix success rate.

After evaluation, replace generic wording with values copied directly from committed raw results; never invent an
improvement percentage.
