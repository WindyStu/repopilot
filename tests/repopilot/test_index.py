import pytest

from minisweagent.repopilot.index import (
    FileRecord,
    ImportRecord,
    RepositoryIndex,
    SourceSpan,
    SymbolRecord,
    build_repository_index,
    index_python_file,
    iter_python_files,
    normalize_repo_path,
)


def test_index_records_round_trip_without_information_loss():
    index = RepositoryIndex(
        version=1,
        files=[
            FileRecord(
                path="src/example.py",
                module="src.example",
                content_hash="abc123",
                imports=[ImportRecord(module="pathlib", names=["Path"], level=0)],
                symbols=[
                    SymbolRecord(
                        kind="function",
                        name="load",
                        qualified_name="load",
                        signature="load(path: str) -> str",
                        docstring="Load a file.",
                        span=SourceSpan(start_line=3, end_line=5),
                    )
                ],
                source="def load(path: str) -> str:\n    return path\n",
            )
        ],
    )

    assert RepositoryIndex.model_validate_json(index.model_dump_json()) == index


def test_normalize_repo_path_returns_posix_relative_path_and_rejects_escape(tmp_path):
    repository = tmp_path / "repo"
    source = repository / "src" / "example.py"
    source.parent.mkdir(parents=True)
    source.write_text("pass\n")
    outside = tmp_path / "outside.py"
    outside.write_text("pass\n")

    assert normalize_repo_path(repository, source) == "src/example.py"
    with pytest.raises(ValueError, match="outside repository"):
        normalize_repo_path(repository, outside)


def test_normalize_repo_path_rejects_symlink_escape(tmp_path):
    repository = tmp_path / "repo"
    repository.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("pass\n")
    link = repository / "linked.py"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("Symlinks are not available")

    with pytest.raises(ValueError, match="outside repository"):
        normalize_repo_path(repository, link)


def test_index_python_file_extracts_imports_and_nested_typed_symbols(tmp_path):
    repository = tmp_path / "repo"
    source = repository / "src" / "parser.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        """from pathlib import Path as P
from .helpers import parse as parse_helper

@registered
class Parser(Base):
    \"\"\"Parse source files.\"\"\"

    async def parse(self, path: P) -> str:
        return parse_helper(path)

def outer(value: int):
    def inner(suffix: str = \"x\") -> str:
        return f\"{value}{suffix}\"
    return inner()
"""
    )

    record = index_python_file(repository, source)
    symbols = {symbol.qualified_name: symbol for symbol in record.symbols}

    assert record.path == "src/parser.py"
    assert record.module == "src.parser"
    assert [(item.module, item.names, item.level) for item in record.imports] == [
        ("pathlib", ["Path as P"], 0),
        ("helpers", ["parse as parse_helper"], 1),
    ]
    assert set(symbols) == {"Parser", "Parser.parse", "outer", "outer.inner"}
    assert symbols["Parser"].kind == "class"
    assert symbols["Parser"].docstring == "Parse source files."
    assert symbols["Parser"].span == SourceSpan(start_line=4, end_line=9)
    assert symbols["Parser.parse"].kind == "method"
    assert symbols["Parser.parse"].signature == "async parse(self, path: P) -> str"
    assert symbols["outer.inner"].signature == "inner(suffix: str='x') -> str"
    assert record.parse_error is None
    assert len(record.content_hash) == 64


def test_index_python_file_retains_metadata_on_syntax_error(tmp_path):
    repository = tmp_path / "repo"
    source = repository / "broken.py"
    repository.mkdir()
    source.write_text("def broken(:\n    pass\n")

    record = index_python_file(repository, source)

    assert record.path == "broken.py"
    assert record.source == "def broken(:\n    pass\n"
    assert record.symbols == []
    assert record.imports == []
    assert "invalid syntax" in record.parse_error
    assert len(record.content_hash) == 64


def test_iter_python_files_honors_gitignores_artifacts_exclusions_and_symlink_safety(tmp_path):
    repository = tmp_path / "repo"
    (repository / "nested").mkdir(parents=True)
    (repository / ".venv" / "lib").mkdir(parents=True)
    (repository / ".git").mkdir()
    (repository / ".gitignore").write_text("ignored.py\n")
    (repository / "nested" / ".gitignore").write_text("skip.py\n")
    for path in [
        repository / "keep.py",
        repository / "ignored.py",
        repository / "generated.py",
        repository / "nested" / "keep.py",
        repository / "nested" / "skip.py",
        repository / ".venv" / "lib" / "dependency.py",
        repository / ".git" / "internal.py",
    ]:
        path.write_text("pass\n")
    outside = tmp_path / "outside.py"
    outside.write_text("pass\n")
    try:
        (repository / "linked.py").symlink_to(outside)
    except OSError:
        pass

    assert [path.relative_to(repository).as_posix() for path in iter_python_files(repository, ["generated.py"])] == [
        "keep.py",
        "nested/keep.py",
    ]


def test_build_repository_index_reuses_unchanged_files_and_invalidates_changed_file(tmp_path):
    repository = tmp_path / "repo"
    repository.mkdir()
    first_file = repository / "first.py"
    second_file = repository / "second.py"
    first_file.write_text("def first():\n    return 1\n")
    second_file.write_text("def second():\n    return 2\n")

    first = build_repository_index(repository)
    second = build_repository_index(repository)
    first_file.write_text("def first():\n    return 3\n")
    third = build_repository_index(repository)

    assert (first.indexed_files, first.reused_files) == (2, 0)
    assert (second.indexed_files, second.reused_files) == (0, 2)
    assert (third.indexed_files, third.reused_files) == (1, 1)
    assert {file.path for file in third.index.files} == {"first.py", "second.py"}
    assert third.index.files[0].content_hash != first.index.files[0].content_hash


def test_build_repository_index_recovers_from_corrupt_cache(tmp_path):
    repository = tmp_path / "repo"
    repository.mkdir()
    (repository / "app.py").write_text("pass\n")
    cache = repository / ".repopilot" / "index.json"
    cache.parent.mkdir()
    cache.write_text("not json")

    result = build_repository_index(repository)

    assert result.indexed_files == 1
    assert result.reused_files == 0
    assert result.warnings == ["Ignoring corrupt or incompatible index cache"]
    assert RepositoryIndex.model_validate_json(cache.read_text()) == result.index
