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

The checked-in end-to-end pilot compares the same 3 fixture tasks once per variant with DeepSeek Flash. Both baseline and
enhanced solved 3/3 tasks and passed 9/9 hidden tests. Enhanced achieved **100% Recall@5**, used **7.5% fewer input tokens**
(5,847 vs 6,320 mean) and **11.8% fewer strong-model calls** (5.00 vs 5.67 mean), while active latency was **7.4% higher**
(9.04 s vs 8.42 s mean). This is a small descriptive pilot, not a statistically significant solve-rate improvement.
The aggregate, raw trajectories, patches, and JUnit reports are in
[`benchmarks/results/e2e-v1-deepseek-flash-r2`](benchmarks/results/e2e-v1-deepseek-flash-r2/).

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
