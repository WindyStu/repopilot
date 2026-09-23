# RepoPilot

RepoPilot is a repository-aware Python coding agent built on top of
[mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent). It turns an issue into a tested patch by combining:

- Python AST indexing and explainable BM25/symbol/dependency retrieval;
- local Qwen3-0.6B task analysis through SGLang, with deterministic fallback;
- DeepSeek Flash for repository-level coding and shell tool calls, with Gemini available as an adapter;
- a disposable, network-disabled, non-root Docker workspace;
- bounded verification-driven repair retries;
- baseline-versus-RAG benchmark records with traceable trajectories.

This fork retains mini-swe-agent's model abstraction, linear agent loop, trajectory format, and execution interfaces. The
indexer, retriever, context packer, local-model router, safe runner, repair workflow, and benchmark metrics live under
`src/minisweagent/repopilot/`.

## Architecture

```text
Issue
  -> Qwen3-0.6B structured analysis (fallback: deterministic extraction)
  -> Python AST index
  -> BM25 + exact symbol/path boosts + one-hop imports
  -> budgeted, explainable context
  -> DeepSeek Flash + mini-swe-agent loop
  -> isolated tests
  -> bounded repair feedback
  -> patch + trajectory + metrics
```

The small local model does query understanding and reranking; it is intentionally not the primary code generator. This
split makes the validated 4 GB RTX 3050 setup useful without pretending a 0.6B model can reliably solve repository bugs.

## Supported environment

- WSL2 Ubuntu 24.04 (the Ubuntu 26.04 distro is not used)
- project stored on the Linux filesystem, recommended path `/home/hp/projects/repopilot`
- Conda environment `repopilot` for the agent
- separate existing Conda environment `sglang` for Qwen3-0.6B
- Docker Desktop with WSL integration enabled for Ubuntu-24.04

Bootstrap the Python environment and verifier image:

```bash
./scripts/bootstrap.sh
conda activate repopilot
```

The script never installs into or changes the `sglang` environment.

## Model setup

The one-command experiment script starts the validated local model with proxy variables removed from the SGLang process:

```bash
./scripts/run_controlled_evaluation.sh
```

For a manual server, use the local ModelScope snapshot and keep loopback traffic out of the VPN proxy:

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy \
  NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost \
  conda run -n sglang repopilot-local serve \
  --model-path /home/hp/.cache/modelscope/models/Qwen--Qwen3-0.6B/snapshots/master
```

Export provider keys only in the WSL shell. The canonical controlled evaluation uses `DEEPSEEK_API_KEY`:

```bash
export DEEPSEEK_API_KEY='your-key'
repopilot-local health
```

RepoPilot checks the key before a run but never stores it in model config, trajectories, Docker arguments, or the target
workspace.

## One-command issue-to-patch run

```bash
repopilot run \
  --repo /home/hp/projects/example-python-repo \
  --issue 'divide(3, 2) returns 1 instead of 1.5' \
  --test-command 'pytest -q'
```

The source checkout is not modified. RepoPilot creates a filtered copy under `artifacts/<run-id>/workspace`, initializes a
local snapshot, mounts only that copy into a network-disabled container, and writes:

- `attempt-N.traj.json` — full model/action trajectory;
- `solution.patch` — diff against the copied baseline;
- `report.json` — verification status and attempt evidence.

Run the controlled shell-exploration baseline with the same strong model and limits:

```bash
repopilot run --baseline --repo /path/to/repo --issue '...' --test-command 'pytest -q'
```

If Qwen is intentionally offline, use `--no-local-model`; deterministic task extraction remains enabled.

## Verification and security defaults

Generated commands run as a numeric non-root user with no network, all Linux capabilities dropped, no-new-privileges,
1 GiB memory, 1 CPU, 128 PIDs, and bounded command time/output. API credentials are not forwarded. Repositories that need
extra dependencies should use a deliberately prebuilt runner image because runtime network access stays disabled.

## Tests and current evidence

```bash
make test
```

Deterministic tests cover local-model parsing/fallbacks, indexing, retrieval evidence, context budgets, credential-safe
provider configuration, Docker command isolation, automatic repair, benchmark aggregation, and issue-to-code-change
fixtures. Live provider and Docker checks are opt-in so CI never consumes credentials or provider quota.

The primary checked-in evaluation contains **20 paired tasks / 40 DeepSeek Flash sessions**: 5 authored fixtures and 15
immutable real-project snapshots from more-itertools, Click, and attrs, split into 5 easy, 10 medium, and 5 hard tasks.
Compared with the no-retrieval baseline, the enhanced workflow improved:

- **Task Success Rate:** 20.0% (4/20) -> **45.0% (9/20)**, +25.0 percentage points;
- **hidden-test case pass rate:** 52.2% (36/69) -> **63.8% (44/69)**, +11.6 percentage points;
- **Retrieval Recall@5:** **92.5%** for the enhanced workflow;
- **mean strong-model calls:** 7.95 -> **7.20**, a 9.4% reduction.

The improvement trades extra context and local analysis for fewer strong-model calls: mean provider-reported input tokens
rose from 15,321 to 24,098 (+57.3%), and mean active time rose from 24.98 s to 27.98 s (+12.0%). Six tasks were solved only
by enhanced, one only by baseline, three by both, and ten by neither. Since each task was run once, these are descriptive
results rather than a statistical-significance claim. The aggregate, all task IDs, raw trajectories, patches, and JUnit
reports are in
[`benchmarks/results/e2e-v2-deepseek-flash-20task`](benchmarks/results/e2e-v2-deepseek-flash-20task/).

The earlier 3-fixture pilot remains available as historical evidence under
[`benchmarks/results/e2e-v1-deepseek-flash-r2`](benchmarks/results/e2e-v1-deepseek-flash-r2/); it is not mixed into the
20-task aggregate.

The checked-in `repopilot-retrieval-v1` result contains 20 labeled tasks: the no-context baseline scores **0% Recall@5**
and deterministic hybrid retrieval scores **90% Recall@5**. This is a retrieval metric, not an end-to-end bug-fix success
rate. Raw per-task results, including both misses, are in
[`docs/repopilot/results/retrieval-v1.json`](docs/repopilot/results/retrieval-v1.json).

See [evaluation](docs/repopilot/evaluation.md) and [interview notes](docs/repopilot/interview.md) for metric definitions,
limitations, and resume wording.

## Attribution

RepoPilot is a derivative of mini-swe-agent and remains under its MIT license. Upstream project and authorship are preserved
in Git history, `LICENSE.md`, and package metadata. RepoPilot-specific claims refer only to the modules and experiments in
this fork, not to upstream SWE-bench results.
