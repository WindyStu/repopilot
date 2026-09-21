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
back to deterministic extraction. DeepSeek Flash performs the harder diagnosis and patching through the existing
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

## Measured result and trade-off

On the checked-in 3-task, single-run paired pilot, both variants solved 3/3 tasks and passed 9/9 hidden tests. Enhanced
retrieval reached 100% Recall@5, reduced average input tokens by 7.5% and strong-model calls by 11.8%, but increased active
latency by 7.4%. The correct conclusion is efficiency improved on this pilot; solve rate did not.

## Resume wording

Chinese:

“基于 mini-swe-agent 开发 RepoPilot：实现 Python AST/BM25/符号与依赖混合检索、本地 Qwen3-0.6B 路由、无网络非 root
Docker 沙箱及失败自动修复；在 DeepSeek Flash 的 3 题同任务配对实验中，完整系统保持 100% 任务/隐藏测试通过率，
Recall@5 达 100%，平均输入 Token 降低 7.5%、强模型调用降低 11.8%（单次小样本实验）。”

English:

“Built RepoPilot on mini-swe-agent with explainable Python retrieval, local Qwen3-0.6B routing, credential-isolated Docker
execution, and bounded repair; on a checked-in 3-task paired DeepSeek Flash pilot, maintained 100% task/hidden-test pass
rates with 100% Recall@5 while reducing mean input tokens 7.5% and strong-model calls 11.8% (single-run pilot).”

For the separate 20-task smoke check, always call 90% a retrieval-only Recall@5 result. Never describe it as a 90% bug-fix
success rate. For the end-to-end pilot, always state the 3-task and single-run limitations.
