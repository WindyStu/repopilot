# RepoPilot E2E v2 20-Task Implementation Plan

Date: 2026-09-22

## Goal

Build, qualify, freeze, execute, and publish a new 20-task mixed Python bug-fix evaluation containing 5 authored fixtures
and 15 permissively licensed real-project snapshots. The final experiment runs 20 baseline/enhanced pairs from one clean
revision and publishes traceable trajectories, patches, JUnit evidence, aggregate metrics, and limitation-aware resume text.

## Stage 1: Manifest v2 and metadata validation

1. Add failing unit tests for schema-version-aware metadata requirements, SPDX allowlisting, immutable source revisions,
   task difficulty, capability category, cross-file flag, and origin URLs.
2. Extend `EvaluationTask` and `EvaluationDataset` without breaking v1 manifests.
3. Add deterministic dataset hashing over the manifest, visible repositories, hidden tests, and reference patches.
4. Verify targeted tests, then the existing RepoPilot suite.

## Stage 2: Qualification records and freeze gate

1. Add failing tests for a qualification API that runs buggy and reference-patched workspaces in Docker.
2. Record buggy/fixed JUnit counts, allowed-path audit, task hash, and qualification status.
3. Add a dataset-level gate that fails atomically when any task is missing metadata, unexpectedly passes while buggy,
   fails after its reference patch, changes forbidden files, or produces inconsistent repeated results.
4. Add a CLI command that writes `qualification.json` and `dataset-lock.json` only after all tasks qualify.
5. Ensure hidden tests and credentials never enter agent workspaces or freeze artifacts.

## Stage 3: Five authored fixtures

Create and qualify five deterministic multi-file fixtures:

1. async retry cancellation and backoff state;
2. cache invalidation across service and repository layers;
3. state-machine transition mutation and rollback;
4. versioned JSON serialization with nested dataclasses;
5. archive/path traversal safety across validation and extraction modules.

Each fixture includes distracting files, at least two relevant labels, three or more hidden cases, an exact allowed-change
set, origin marked `authored`, and a zero-context reference patch.

## Stage 4: Fifteen real-project snapshots

1. Search permissively licensed Python projects for small historical fixes that can run offline on Python 3.12.
2. Prefer defects involving parsing, configuration, collections, caching, paths, serialization, async control flow, and
   cross-file calls; exclude security embargoes, huge generated code, flaky tests, and dependency-heavy integration bugs.
3. For every candidate, verify upstream repository, immutable pre-fix revision, issue/PR or fixing commit, and license from
   primary upstream sources.
4. Minimize each snapshot while retaining realistic repository noise, attribution notices, and enough files for retrieval
   to matter.
5. Adapt upstream reproduction tests into external hidden tests without copying unnecessary copyrighted material.
6. Generate a clean reference patch and qualify buggy/fixed states in Docker.
7. Replace rejected candidates until exactly 15 real tasks qualify and the required difficulty/cross-file distribution is
   satisfied.

## Stage 5: Dataset-wide integrity and dry runs

1. Add tests that assert exactly 20 tasks, 5 authored/15 real, 5 easy/10 medium/5 hard, at least 12 cross-file tasks, and
   at least 8 tasks with three or more plausible source files.
2. Run qualification twice and compare task hashes and JUnit counts.
3. Run secret, hidden-test leakage, license metadata, path escape, reference-patch, and issue-hint scans.
4. Commit the frozen v2 dataset and lock file before paid calls.
5. Run two separate non-reportable dry-run tasks through both variants to validate Qwen health, DeepSeek tool use, Docker,
   artifact persistence, and balance checks.

## Stage 6: Formal 20-pair experiment and publication

1. Start Qwen with loopback proxies disabled and pass structured-generation health.
2. Record DeepSeek starting balance and the clean Git/Docker/dataset identifiers.
3. Run all affordable indivisible pairs sequentially with alternating order and the existing CNY 8/CNY 2 guard.
4. Require 20 complete eligible pairs before describing the result as the v2 20-task experiment.
5. Recompute aggregate JSON and Markdown from raw session JSON; verify the six requested metrics and all denominators.
6. Copy only trajectories, session reports, patches, JUnit, state, lock, and aggregate files into the tracked result tree.
7. Scan artifacts for credentials, Codex files, workspaces, nested Git data, and user-specific secrets.
8. Update README, evaluation notes, interview narrative, and resume wording with exact results and single-run limitations.
9. Run the complete test suite and static checks, commit, push to GitHub, and verify remote HEAD.

## TDD and commit discipline

Every new production behavior begins with a focused failing test whose failure is observed. Implement only enough behavior
to pass, then refactor with the suite green. Fixture data is validated by executable qualification tests before it is used.
Commits are separated into schema/qualification infrastructure, authored fixtures, real snapshots and freeze record, and
formal experiment/report publication.
