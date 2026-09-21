# RepoPilot Controlled Evaluation Implementation Plan

Design: `docs/superpowers/specs/2026-09-21-repopilot-controlled-evaluation-design.md`

## 1. DeepSeek provider and budget boundary

- Add failing tests for credential preflight, non-serialization, `deepseek/deepseek-flash`, call/output limits, and balance
  response parsing without persisting authorization data.
- Implement the provider builder, balance client, and CNY budget guard.
- Add an opt-in live Bash tool-call and balance smoke test.

## 2. Versioned end-to-end fixture dataset

- Define a manifest schema for repository template, issue, relevant files, allowed changes, public tests, hidden tests, and
  commands.
- Add failing schema/integrity tests.
- Build and validate three pilot fixtures whose buggy state fails hidden tests and reference patch passes them.
- Expand only after pilot cost forecasting, up to 20 fixtures.

## 3. Hidden Docker verification

- Add failing tests for read-only hidden-test mounts, writable artifact output, forbidden-change detection, JUnit parsing,
  and credential absence.
- Implement hidden verification without exposing tests to the agent workspace.
- Run a real Docker integration test.

## 4. Metrics and immutable session records

- Add failing tests for input/cache token extraction, calls, active versus waiting time, test-case pass counts, retrieval
  Recall@5, failure classes, and strict task success.
- Implement JSONL records and deterministic aggregation.

## 5. Paired resumable scheduler

- Add failing tests for alternating order, indivisible pairs, resume behavior, three-pair forecast, balance floor, and
  atomic result writes.
- Implement sequential baseline/enhanced execution with bounded transient retries.
- Add dry-run output showing planned calls, paths, and budget without contacting providers.

## 6. Qualification and pilot

- Run all unit and Docker integration tests plus secret scans.
- Start Qwen and verify structured health.
- Run one DeepSeek tool-call smoke test and record model identity/usage.
- Record starting CNY balance.
- Execute three task pairs, checking balance after every complete pair.
- Produce raw JSONL, aggregate JSON/Markdown, patches, trajectories, JUnit, and a cost forecast.
- Review pilot validity before automatically continuing to more pairs.

## 7. Full report and portfolio update

- Continue up to 20 pairs while forecast cost remains within the CNY 8 cap.
- Recalculate reports only from immutable raw sessions.
- Update README, evaluation documentation, interview narrative, and resume bullet from the final measured denominators.
- Run final tests, credential scan, commit, and push.
