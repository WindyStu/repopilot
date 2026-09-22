# RepoPilot E2E v2 20-Task Evaluation Design

Date: 2026-09-22

## Objective

Create and freeze a new 20-task Python bug-fix dataset, then compare RepoPilot's retrieval-assisted workflow with the
no-retrieval mini-swe-agent baseline in 20 paired runs. The final result must measure end-to-end issue-to-patch behavior,
not reuse the existing 20-query retrieval smoke benchmark or the 3-task v1 pilot.

The experiment is designed to reveal genuine retrieval effects through repository structure, irrelevant files, indirect
call sites, and cross-file dependencies. Tasks must not be edited after model execution begins, and task wording must not
be manipulated to make either variant win.

## Dataset composition

The versioned dataset is named `repopilot-e2e-v2` and contains exactly 20 independent tasks:

- 5 authored fixtures covering async behavior, cache invalidation, state mutation, serialization, and path safety;
- 15 offline snapshots derived from real defects in permissively licensed Python open-source projects.

The difficulty distribution is fixed at 5 easy, 10 medium, and 5 hard tasks. At least 12 tasks require understanding more
than one source file, even when the final patch changes only one file. At least 8 tasks have three or more plausible source
files so that retrieval is not reduced to selecting the only implementation file.

Each real task records the upstream repository URL, immutable source revision, upstream issue or patch URL, license SPDX
identifier, files retained in the minimized snapshot, and adaptations made for offline deterministic execution. Source
projects must use MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0, ISC, or PSF-2.0-compatible licensing. Copyright and license
notices required by the upstream project are retained.

No task may depend on network access, databases, services, nondeterministic clocks, or platform-specific behavior. Runtime
dependencies must already exist in the `repopilot-runner:py312` image or be represented by a small deterministic local
test double that is part of the visible repository.

## Task contract

Every task contains:

- a frozen buggy repository under `repo/`;
- an issue statement that describes externally visible behavior without naming the answer file unless the upstream issue
  itself does so;
- at least one manually labeled relevant source file;
- public tests or examples visible to the agent when they are part of the upstream reproduction;
- acceptance and regression tests under a hidden directory outside the writable workspace;
- an exact allowed source-file change set;
- a zero-context reference patch;
- deterministic public and hidden test commands;
- metadata for origin, license, difficulty, capability category, and whether cross-file reasoning is required.

The manifest schema is extended rather than replaced. Existing v1 manifests remain loadable. New metadata fields are
required for v2 and validated when the dataset declares schema version 2.

## Qualification and leakage controls

All 20 tasks must pass qualification before any paid experiment begins:

1. The buggy snapshot runs successfully but fails at least one hidden test for the intended defect.
2. The reference patch applies cleanly and makes every public and hidden test pass.
3. The reference patch changes only the declared allowed paths.
4. Hidden test files and their contents never appear in the materialized agent workspace or prompt.
5. The issue does not contain reference-patch text, hidden assertion values, or artificial file-name hints.
6. Relevant-file labels identify source needed to understand the defect, not only files changed by the reference patch.
7. Repeated qualification produces identical pass/fail counts.
8. Every real task has complete origin and license metadata.

An automated integrity report records the buggy and fixed JUnit counts, patch paths, relevant labels, license metadata,
and a content hash for every task. Qualification failure blocks the entire paid run; tasks are never silently skipped.

## Variants and fairness

Both variants use DeepSeek `deepseek-flash`, temperature 0, at most 2,048 output tokens per response, at most 8 strong-model
calls per session, at most one verification-driven repair, the same prompt apart from retrieved context, the same Docker
image, and the same active-time limit.

Baseline receives the issue and writable repository only. Retrieval and Qwen analysis are disabled. Enhanced receives the
Python AST/BM25/exact-symbol/path/dependency retrieval context plus local Qwen3-0.6B structured task analysis. A Qwen health
check with real structured generation is required before scheduling. Any enhanced fallback remains in raw evidence but is
ineligible for the primary complete-system aggregate.

Pair order alternates by task. A pair is indivisible for budget scheduling. The dataset and harness Git revision, Docker
image identifier, provider model, balance observations, and run timestamps are recorded. Two framework-only dry runs may
be used before the formal experiment, but they use separate tasks and are excluded from the 20-task dataset and report.

## Budget and execution

The scheduler keeps the existing maximum measured spend of CNY 8 and minimum ending balance of CNY 2. It checks balance
before the experiment and after each complete pair. The initial estimated pair cost is CNY 1.50 and is replaced by a
conservative forecast after completed pairs when the provider balance has sufficient precision. If the next complete pair
cannot fit the budget, execution stops without starting either half; the partial scope is reported and is not presented as
a 20-task result.

The formal experiment runs sequentially from a clean, committed revision into a new immutable result directory. Completed
sessions are never overwritten. Infrastructure failure, rate limiting, Qwen fallback, invalid patch, forbidden change,
test failure, model failure, and step/time limits remain distinct failure classes.

## Metrics and reporting

The primary report contains, per variant:

- Task Success Rate with numerator and denominator;
- hidden-test case pass rate with raw counts;
- enhanced Retrieval Recall@5 and baseline `N/A`;
- total and mean provider-reported input tokens;
- total and mean strong-model calls;
- total and mean active wall time;
- failure-class counts and task-level outcomes.

Paired enhanced-minus-baseline deltas and relative changes are computed from immutable session JSON. The report includes
all task IDs, not only wins. With one run per task, results are descriptive and make no statistical-significance claim.
The README and resume wording are updated only after 20 complete eligible pairs exist and all raw trajectories, patches,
JUnit files, origin metadata, and aggregate calculations pass a secret scan.

## Expected implementation

Implementation is divided into four bounded stages:

1. Extend the v2 manifest schema, origin/license validation, qualification records, and integrity tests using TDD.
2. Create and qualify the 5 authored fixtures and 15 real-project offline snapshots without paid model calls.
3. Add a frozen-dataset command that emits hashes and refuses any later mutation or incomplete qualification.
4. Run the 40 formal sessions, generate reports, update documentation and resume metrics, run the full test suite and secret
   scan, then commit and push the artifacts.

The v1 pilot and retrieval smoke benchmark remain unchanged and clearly labeled. No v1 session is included in the v2
aggregate.
