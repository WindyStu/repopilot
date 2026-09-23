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

On the checked-in 20-task paired evaluation, the enhanced workflow improved Task Success Rate from 20.0% (4/20) to 45.0%
(9/20), and hidden-test case pass rate from 52.2% (36/69) to 63.8% (44/69). Retrieval Recall@5 was 92.5%, while mean
strong-model calls fell from 7.95 to 7.20 (-9.4%). The trade-off is important: mean input tokens increased 57.3% and mean
active time increased 12.0%. Six tasks were enhanced-only wins, one was a baseline-only win, three were solved by both, and
ten by neither. With one run per task, describe this as a measured result, not a statistically significant claim.

## Resume wording

Chinese:

“基于 mini-swe-agent 开发 RepoPilot 编码 Agent：实现 Python AST + BM25 + 符号/依赖混合 RAG、本地
Qwen3-0.6B 任务路由、无网络非 root Docker 沙箱及隐藏测试驱动的自动修复；构建 20 题混合基准并完成 40 次
DeepSeek Flash 配对实验，使任务成功率由 20% 提升至 45%（+25 个百分点）、隐藏测试通过率提升 11.6 个百分点，
Recall@5 达 92.5%，强模型平均调用次数降低 9.4%。”

English:

“Built RepoPilot on mini-swe-agent with explainable AST/BM25/symbol/dependency RAG, local Qwen3-0.6B routing,
network-disabled non-root Docker execution, and hidden-test-driven repair; created a 20-task mixed benchmark and ran 40
paired DeepSeek Flash sessions, improving task success from 20% to 45% (+25 pp) and hidden-test pass rate by 11.6 pp, with
92.5% Recall@5 and 9.4% fewer strong-model calls.”

Keep the separate 90% result labeled as a retrieval-only smoke check; never describe it as a bug-fix success rate. For the
end-to-end v2 result, state that it is 20 tasks with one run per variant and avoid statistical-significance language.
