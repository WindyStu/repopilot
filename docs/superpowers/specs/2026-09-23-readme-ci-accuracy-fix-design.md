# RepoPilot README and CI Accuracy Fix

Date: 2026-09-23

## Goal

Correct two repository-quality issues without changing RepoPilot''s retrieval behavior:

1. Describe Qwen3-0.6B accurately as structured query understanding and retrieval-term extraction, not as a reranker.
2. Restrict GitHub Actions pytest collection to the maintained project test suite so benchmark fixtures and examples are
   not collected as CI tests.

## Documentation behavior

RepoPilot''s retrieval order remains deterministic. Qwen produces a structured task analysis containing identifiers, paths,
exceptions, and search terms. The deterministic retriever then ranks indexed files using BM25-style lexical scoring, exact
symbol/path boosts, and one-hop dependency expansion.

README wording will explicitly preserve that boundary. Related interview and evaluation documentation will be checked for
claims that imply Qwen directly scores or reorders candidates. Accurate references to local-model task analysis or routing
will remain.

No reranking API, prompt, score, benchmark, or runtime behavior will be added in this change. Existing v2 experimental
results remain valid because they measured the current query-analysis plus deterministic-retrieval architecture.

## CI behavior

The Pytest GitHub Actions workflow will invoke pytest with the explicit `tests/` path while retaining its existing
verbosity, coverage, branch-coverage, XML-report, and xdist options. This prevents recursive discovery under
`benchmarks/` and `examples/`.

The scope is limited to pytest collection. Pylint, documentation, link checking, release workflows, and benchmark-specific
qualification commands remain unchanged.

## Test strategy

TDD will be used for the workflow fix:

1. Add a repository test that parses `.github/workflows/pytest.yaml` and requires the Run pytest command to target
   `tests/`.
2. Run that test against the existing workflow and confirm it fails because the path is absent.
3. Change the workflow command minimally and confirm the focused test passes.
4. Run the complete maintained suite with an explicit `tests/` path.
5. Check documentation for the obsolete reranking claim and inspect the final diff.

Documentation-only wording does not require a runtime unit test, but the obsolete claim will be checked directly.

## Acceptance criteria

- README no longer says or implies that Qwen reranks retrieval candidates.
- README accurately separates Qwen query analysis from deterministic ranking.
- Related RepoPilot documentation contains no contradictory reranking claim.
- GitHub Actions runs pytest against `tests/` explicitly.
- The new workflow regression test passes.
- The complete maintained test suite passes when invoked with the same explicit test root used by CI.
- No benchmark result, credential, generated local artifact, or retrieval implementation is modified.
