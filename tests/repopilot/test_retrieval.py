from minisweagent.repopilot.index import FileRecord, ImportRecord, RepositoryIndex, SourceSpan, SymbolRecord
from minisweagent.repopilot.retrieval import retrieve
from minisweagent.repopilot.task_analysis import TaskAnalysis


def file_record(path, source, symbols=None, module=None):
    return FileRecord(
        path=path,
        module=module or path.removesuffix(".py").replace("/", "."),
        content_hash=path,
        symbols=symbols or [],
        source=source,
    )


def analysis(search_terms, identifiers=None, paths=None, exceptions=None):
    return TaskAnalysis(
        task_type="bugfix",
        identifiers=identifiers or [],
        paths=paths or [],
        exceptions=exceptions or [],
        search_terms=search_terms,
    )


def test_retrieve_exact_symbol_outranks_incidental_source_match_with_evidence():
    index = RepositoryIndex(
        version=1,
        files=[
            file_record(
                "src/parser.py",
                "def parse_value(value):\n    return value\n",
                [
                    SymbolRecord(
                        kind="function",
                        name="parse_value",
                        qualified_name="parse_value",
                        signature="parse_value(value)",
                        docstring=None,
                        span=SourceSpan(start_line=1, end_line=2),
                    )
                ],
            ),
            file_record("src/docs.py", "# parse_value is documented here\n"),
        ],
    )

    results = retrieve(index, analysis(["parse_value"], identifiers=["parse_value"]))

    assert [result.path for result in results] == ["src/parser.py", "src/docs.py"]
    assert results[0].score_breakdown["exact_symbol"] > 0
    assert results[0].score_breakdown["lexical"] > 0
    assert results[1].score_breakdown["exact_symbol"] == 0
    assert results[1].matched_terms == ["parse_value"]


def test_retrieve_path_and_exception_terms_influence_ranking():
    index = RepositoryIndex(
        version=1,
        files=[
            file_record("src/decoder.py", "raise ValueError('bad payload')\n"),
            file_record("src/encoder.py", "raise ValueError('bad value')\n"),
        ],
    )

    results = retrieve(
        index,
        analysis(
            ["src/decoder.py", "ValueError"],
            paths=["src/decoder.py"],
            exceptions=["ValueError"],
        ),
    )

    assert results[0].path == "src/decoder.py"
    assert results[0].score_breakdown["exact_path"] > 0
    assert results[1].score_breakdown["exact_path"] == 0


def test_retrieve_uses_path_as_deterministic_tie_breaker():
    index = RepositoryIndex(
        version=1,
        files=[file_record("zeta.py", "shared token\n"), file_record("alpha.py", "shared token\n")],
    )

    assert [result.path for result in retrieve(index, analysis(["shared"]))] == ["alpha.py", "zeta.py"]


def test_retrieve_adds_only_one_hop_dependencies_and_terminates_cycles():
    api = file_record("src/api.py", "def handle():\n    pass\n", module="src.api")
    api.imports = [ImportRecord(module="src.helpers", names=["parse"])]
    helpers = file_record("src/helpers.py", "def parse():\n    pass\n", module="src.helpers")
    helpers.imports = [ImportRecord(module="src.api", names=["handle"])]
    unrelated = file_record("src/common.py", "def common():\n    pass\n", module="src.common")
    index = RepositoryIndex(version=1, files=[api, helpers, unrelated])

    results = retrieve(index, analysis(["src/api.py"], paths=["src/api.py"]))

    assert [result.path for result in results] == ["src/api.py", "src/helpers.py"]
    assert results[1].score_breakdown["dependency"] > 0
    assert len({result.path for result in results}) == len(results)
