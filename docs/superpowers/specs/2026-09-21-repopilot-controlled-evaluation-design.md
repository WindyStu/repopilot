# RepoPilot Controlled Baseline Evaluation Design

Date: 2026-09-21

## Objective

Measure whether the complete RepoPilot retrieval-assisted workflow improves a minimal shell-exploration baseline under a
strict paired experiment. The experiment must collect raw evidence for task success, retrieval quality, strong-model input
tokens and calls, active wall time, and post-change hidden-test pass rate. Resume claims may be updated only from committed
raw results produced by this protocol.

The canonical strong model is DeepSeek `deepseek-flash`. Every paired comparison uses the same provider model, model
parameters, task revision, Docker image, call/step limits, retry policy, and verification commands. Gemma 4 31B is outside
the primary aggregate and may be evaluated later as a separately reported robustness experiment.

## Budget and scheduling

The account has approximately CNY 10 available. The harness records the starting DeepSeek CNY balance using
`GET /user/balance` and enforces a maximum measured spend of CNY 8, preserving about CNY 2 as a safety reserve.

The first phase runs three paired tasks. After each complete pair, the harness records the balance delta and forecasts the
number of additional pairs affordable within the remaining experiment budget. It then continues to at most 20 task pairs.
A pair is indivisible: the scheduler never starts a pair unless the estimated remaining budget can cover both variants.

Runs are sequential. The order alternates by task (`baseline -> enhanced`, then `enhanced -> baseline`) to reduce temporal
provider bias. Provider throttling and backoff waiting are measured separately from active task time. A `429`, `408`, or
`5xx` response receives bounded exponential backoff with jitter and is classified as infrastructure failure only after the
retry budget is exhausted.

Each agent session has these hard limits:

- at most 8 strong-model calls;
- at most 2,048 output tokens per strong-model response;
- at most 12,000 characters of retrieved code context;
- one initial attempt plus at most one verification-driven repair;
- at most 15 minutes active wall time;
- existing Docker CPU, memory, PID, network, credential, and output limits.

## Variants

### Baseline

The upstream-style mini-swe-agent shell loop receives the issue and repository but no precomputed repository context.
RepoPilot retrieval and local Qwen analysis are disabled. Docker execution, prompts unrelated to retrieved context, strong
model, limits, verification, artifacts, and retry policy remain identical to the enhanced variant.

### Enhanced

The same loop receives RepoPilot's Python AST index, BM25 ranking, exact symbol/path boosts, one-hop dependency expansion,
bounded context pack, and local Qwen3-0.6B task analysis. The Qwen health check must pass before an enhanced run. A fallback
during a measured run is recorded and makes that run ineligible for the primary full-system comparison; it remains in raw
results as an infrastructure/fallback outcome.

The comparison therefore estimates the effect of the complete RepoPilot retrieval and local-analysis layer, not the effect
of any one retrieval component in isolation.

## Task dataset

The dataset contains up to 20 small, independent Python fixture repositories. It does not use RepoPilot's own source tree.
Each task includes:

- a frozen buggy repository template;
- an issue statement that does not reveal the patch;
- one or more manually labeled relevant source files;
- optional public tests available to the agent;
- hidden acceptance and regression tests stored outside the writable workspace;
- an allowed source-file change set;
- a deterministic test command and dataset version.

Tasks cover arithmetic and boundary conditions, parsing, state mutation, path handling, configuration defaults, exceptions,
cross-file imports, collections, serialization, and async behavior. Before the experiment, every fixture must fail at least
one hidden test in its buggy state and pass all hidden tests after applying its reference patch.

The agent cannot read or modify hidden tests. Modifying public tests, generated benchmark metadata, or files outside the
allowed source set makes the task unsuccessful even if tests pass.

## Execution flow

1. Validate the DeepSeek key with a one-call Bash tool-use smoke test without logging the key.
2. Query and record only numeric/currency balance fields; never persist credentials or authorization headers.
3. Validate Docker isolation, the runner image digest, Qwen health, dataset integrity, and the clean Git revision.
4. Materialize a fresh writable repository copy for one `(task, variant)` session.
5. Run the agent and retain every trajectory and provider usage record.
6. Run hidden tests from a read-only external mount and emit JUnit XML into the run artifact directory.
7. Validate changed paths, capture a binary patch, and classify the outcome.
8. Finish the other half of the pair before aggregating or checking the budget for another pair.
9. Persist the pair atomically, update the resumable run state, and query the new balance.
10. After three pilot pairs, forecast affordable scope and continue without exceeding 20 pairs or the CNY 8 spend cap.
11. Recalculate all aggregate reports from immutable raw records.

An interrupted experiment resumes only missing sessions. Completed session directories are immutable; reruns use a new
replicate identifier rather than overwriting data.

## Metric definitions

### Task Success Rate

A task succeeds only when a non-empty patch changes only allowed source files, all hidden acceptance/regression tests pass,
the agent terminates normally, and no infrastructure or policy violation occurs. The denominator includes every scheduled
task, including provider failures and exhausted retries; infrastructure failures are also reported separately.

### Retrieval Recall@5

For enhanced runs, Recall@5 is the fraction of manually labeled relevant files appearing in the first five retrieved file
paths. It is averaged across tasks with labels. Baseline retrieval Recall@5 is reported as `N/A`, not zero.

### Average input tokens

Sum provider-reported strong-model input tokens across all calls in a session, then report the arithmetic mean per task for
each variant. Cache-hit and cache-miss input tokens are retained separately when the provider supplies them. Qwen tokens are
not included in this metric and are reported separately if available.

### Strong-model calls

Report total calls, mean calls per task, and the distribution per task. Failed billable calls remain included when usage is
available. Balance queries and Qwen requests are excluded.

### Average time

Primary latency is active wall time from agent start through final verification, excluding deliberate scheduler sleeps and
provider rate-limit backoff. Also report end-to-end elapsed time including waiting so operational cost remains visible.

### Post-change test pass rate

Parse JUnit XML and compute total hidden test cases passed divided by total hidden test cases executed. This differs from
Task Success Rate: a partially correct patch can pass some tests but still fail the task.

## Reporting and statistical limits

Produce JSONL session records, a machine-readable aggregate JSON report, a Markdown comparison, patches, JUnit files, and
model trajectories. The aggregate contains paired per-task deltas and raw numerator/denominator counts. With one replicate
per task, claims are descriptive and include task-level outcomes; they do not claim statistical significance. If budget
later permits repeated runs, repeats are appended as a new replicate and confidence intervals are computed without changing
the original records.

The report distinguishes model failure, rate limiting, network failure, Docker/infrastructure failure, invalid patch,
forbidden modification, test failure, step/time limit, and successful completion.

## Resume update gate

Resume and README metrics are updated only if:

- at least three complete pairs exist;
- both variants have identical task IDs and replicate IDs;
- raw records, trajectories, patches, and tests are traceable from the report;
- the report is reproducible from raw records;
- no credentials or user-specific secret values appear in artifacts;
- wording states the exact dataset size, model, and single-run limitation.

The existing 20-task self-retrieval smoke benchmark remains labeled as an internal deterministic check and is not combined
with this end-to-end result.

## Expected implementation boundaries

- provider configuration and credential-safe DeepSeek smoke/balance client;
- immutable fixture dataset and hidden-test validator;
- paired, resumable, budget-aware scheduler;
- session metric extractor for LiteLLM trajectories and JUnit;
- deterministic report generator;
- tests using fake provider/balance responses before any live experiment;
- opt-in live qualification and experiment commands.
