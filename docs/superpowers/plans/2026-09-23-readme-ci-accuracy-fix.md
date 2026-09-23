# RepoPilot README and CI Accuracy Fix Plan

Design: `docs/superpowers/specs/2026-09-23-readme-ci-accuracy-fix-design.md`

1. Add a focused regression test that requires the Pytest GitHub Actions command to pass `tests/` explicitly.
2. Run the focused test and confirm it fails against the current root-scoped command.
3. Update only the workflow command, then rerun the focused test.
4. Replace the README reranking claim with accurate Qwen query-understanding and retrieval-term-extraction wording.
5. Scan RepoPilot documentation for contradictory reranking claims.
6. Run the complete suite using the exact explicit test root used by CI.
7. Inspect, commit, push, and verify the GitHub workflow result.
