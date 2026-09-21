# RepoPilot

RepoPilot is a repository-aware Python coding agent built on top of
[mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent). It turns an issue into a tested patch by combining:

- Python AST indexing and explainable BM25/symbol/dependency retrieval;
- local Qwen3-0.6B task analysis through SGLang, with deterministic fallback;
- Gemini 3.8 Flash for repository-level coding and shell tool calls;
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
  -> Gemini 3.8 Flash + mini-swe-agent loop
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

Start the already validated local model profile in one terminal:

```bash
conda activate sglang
repopilot-local serve
```

The wrapper uses the local ModelScope snapshot and binds to `127.0.0.1:30000` by default. Check both model listing and
structured generation with:

```bash
conda activate repopilot
repopilot-local health
```

Rotate any key that has appeared in chat or logs. Export the replacement only in the current WSL shell:

```bash
export GEMINI_API_KEY='your-new-key'
make live-gemini
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
Gemini configuration, Docker command isolation, automatic repair, benchmark aggregation, and an issue-to-code-change fixture.
The live Gemini and live Docker checks are opt-in so CI never consumes credentials or provider quota.

The checked-in `repopilot-retrieval-v1` result contains 20 labeled tasks: the no-context baseline scores **0% Recall@5**
and deterministic hybrid retrieval scores **90% Recall@5**. This is a retrieval metric, not an end-to-end bug-fix success
rate. Raw per-task results, including both misses, are in
[`docs/repopilot/results/retrieval-v1.json`](docs/repopilot/results/retrieval-v1.json).

Do not put success-rate claims on a resume until both variants have run on the same checked-in benchmark and the generated
raw results are committed. See [evaluation](docs/repopilot/evaluation.md) and [interview notes](docs/repopilot/interview.md).

## Attribution

RepoPilot is a derivative of mini-swe-agent and remains under its MIT license. Upstream project and authorship are preserved
in Git history, `LICENSE.md`, and package metadata. RepoPilot-specific claims refer only to the modules and experiments in
this fork, not to upstream SWE-bench results.
