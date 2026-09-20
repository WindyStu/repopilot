from minisweagent.repopilot.context import pack_context
from minisweagent.repopilot.index import FileRecord, RepositoryIndex, SourceSpan, SymbolRecord
from minisweagent.repopilot.retrieval import RetrievalResult


def result(path, score, matched_terms):
    return RetrievalResult(
        path=path,
        score=score,
        score_breakdown={"lexical": score, "exact_symbol": 0, "exact_path": 0, "dependency": 0},
        matched_terms=matched_terms,
    )


def test_pack_context_selects_complete_matching_symbol():
    source = "def unrelated():\n    return 0\n\ndef parse_value(value):\n    return int(value)\n"
    index = RepositoryIndex(
        version=1,
        files=[
            FileRecord(
                path="parser.py",
                module="parser",
                content_hash="hash",
                source=source,
                symbols=[
                    SymbolRecord(
                        kind="function",
                        name="unrelated",
                        qualified_name="unrelated",
                        signature="unrelated()",
                        docstring=None,
                        span=SourceSpan(start_line=1, end_line=2),
                    ),
                    SymbolRecord(
                        kind="function",
                        name="parse_value",
                        qualified_name="parse_value",
                        signature="parse_value(value)",
                        docstring=None,
                        span=SourceSpan(start_line=4, end_line=5),
                    ),
                ],
            )
        ],
    )

    packed = pack_context(index, [result("parser.py", 10, ["parse_value"])], budget_chars=200)

    assert len(packed.excerpts) == 1
    assert packed.excerpts[0].span == SourceSpan(start_line=4, end_line=5)
    assert packed.excerpts[0].content == "def parse_value(value):\n    return int(value)"
    assert "unrelated" not in packed.text
    assert packed.used_chars <= packed.budget_chars


def test_pack_context_merges_overlaps_and_drops_lower_ranked_excerpt_before_truncating():
    high_source = "class Parser:\n    def parse(self):\n        return 1\n\n    marker = True\n"
    low_source = "def helper():\n    return 'lower ranked'\n"
    high = FileRecord(
        path="parser.py",
        module="parser",
        content_hash="high",
        source=high_source,
        symbols=[
            SymbolRecord(
                kind="class",
                name="Parser",
                qualified_name="Parser",
                signature="Parser()",
                docstring=None,
                span=SourceSpan(start_line=1, end_line=5),
            ),
            SymbolRecord(
                kind="method",
                name="parse",
                qualified_name="Parser.parse",
                signature="parse(self)",
                docstring=None,
                span=SourceSpan(start_line=2, end_line=3),
            ),
        ],
    )
    low = FileRecord(
        path="helper.py",
        module="helper",
        content_hash="low",
        source=low_source,
        symbols=[],
    )
    index = RepositoryIndex(version=1, files=[high, low])
    ranked = [result("parser.py", 10, ["Parser", "Parser.parse"]), result("helper.py", 2, ["helper"])]
    high_only = pack_context(index, ranked[:1], budget_chars=1_000)

    packed = pack_context(index, ranked, budget_chars=high_only.used_chars)

    assert packed.text == high_only.text
    assert len(packed.excerpts) == 1
    assert packed.excerpts[0].span == SourceSpan(start_line=1, end_line=5)
    assert packed.excluded_paths == ["helper.py"]
    assert packed == pack_context(index, ranked, budget_chars=high_only.used_chars)
