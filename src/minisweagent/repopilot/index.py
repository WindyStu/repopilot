import ast
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pathspec import GitIgnoreSpec
from pydantic import BaseModel


class SourceSpan(BaseModel):
    start_line: int
    end_line: int


class ImportRecord(BaseModel):
    module: str
    names: list[str]
    level: int = 0


class SymbolRecord(BaseModel):
    kind: Literal["class", "function", "method"]
    name: str
    qualified_name: str
    signature: str
    docstring: str | None
    span: SourceSpan


class FileRecord(BaseModel):
    path: str
    module: str
    content_hash: str
    imports: list[ImportRecord] = []
    symbols: list[SymbolRecord] = []
    source: str
    parse_error: str | None = None


class RepositoryIndex(BaseModel):
    version: int
    files: list[FileRecord]


@dataclass(frozen=True)
class IndexBuildResult:
    index: RepositoryIndex
    indexed_files: int
    reused_files: int
    warnings: list[str]


_ARTIFACT_DIRECTORIES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}
_INDEX_VERSION = 1


def normalize_repo_path(repository: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repository.resolve()).as_posix()
    except ValueError as error:
        raise ValueError(f"Path is outside repository: {path}") from error


def _ignore_specs(repository: Path) -> list[tuple[Path, GitIgnoreSpec]]:
    return [
        (path.parent, GitIgnoreSpec.from_lines(path.read_text().splitlines()))
        for path in sorted(repository.rglob(".gitignore"))
        if not _ARTIFACT_DIRECTORIES.intersection(path.relative_to(repository).parts)
    ]


def iter_python_files(repository: Path, exclusions: list[str] | None = None) -> list[Path]:
    repository = repository.resolve()
    specs = _ignore_specs(repository)
    exclusion_spec = GitIgnoreSpec.from_lines(exclusions or [])
    result = []
    for path in sorted(repository.rglob("*.py")):
        relative = path.relative_to(repository)
        if path.is_symlink() or _ARTIFACT_DIRECTORIES.intersection(relative.parts):
            continue
        if exclusion_spec.match_file(relative.as_posix()):
            continue
        if any(
            spec.match_file(path.relative_to(base).as_posix())
            for base, spec in specs
            if path.is_relative_to(base)
        ):
            continue
        result.append(path)
    return result


def _alias_name(alias: ast.alias) -> str:
    if alias.asname:
        return f"{alias.name} as {alias.asname}"
    return alias.name


def _span(node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> SourceSpan:
    return SourceSpan(
        start_line=min([node.lineno, *(decorator.lineno for decorator in node.decorator_list)]),
        end_line=node.end_lineno or node.lineno,
    )


def _function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
    returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    return f"{prefix}{node.name}({ast.unparse(node.args)}){returns}"


class _IndexVisitor(ast.NodeVisitor):
    def __init__(self):
        self.imports: list[ImportRecord] = []
        self.symbols: list[SymbolRecord] = []
        self.parents: list[tuple[str, str]] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(ImportRecord(module=alias.name, names=[_alias_name(alias)]))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.imports.append(
            ImportRecord(module=node.module or "", names=[_alias_name(alias) for alias in node.names], level=node.level)
        )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        qualified_name = ".".join([*(name for name, _ in self.parents), node.name])
        arguments = ", ".join([*(ast.unparse(base) for base in node.bases), *(ast.unparse(k) for k in node.keywords)])
        self.symbols.append(
            SymbolRecord(
                kind="class",
                name=node.name,
                qualified_name=qualified_name,
                signature=f"{node.name}({arguments})",
                docstring=ast.get_docstring(node, clean=False),
                span=_span(node),
            )
        )
        self.parents.append((node.name, "class"))
        self.generic_visit(node)
        self.parents.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.symbols.append(
            SymbolRecord(
                kind="method" if self.parents and self.parents[-1][1] == "class" else "function",
                name=node.name,
                qualified_name=".".join([*(name for name, _ in self.parents), node.name]),
                signature=_function_signature(node),
                docstring=ast.get_docstring(node, clean=False),
                span=_span(node),
            )
        )
        self.parents.append((node.name, "function"))
        self.generic_visit(node)
        self.parents.pop()


def index_python_file(repository: Path, path: Path) -> FileRecord:
    relative_path = normalize_repo_path(repository, path)
    source = path.read_text()
    module_parts = list(Path(relative_path).with_suffix("").parts)
    if module_parts[-1] == "__init__":
        module_parts.pop()
    record = FileRecord(
        path=relative_path,
        module=".".join(module_parts),
        content_hash=hashlib.sha256(source.encode()).hexdigest(),
        source=source,
    )
    try:
        tree = ast.parse(source, filename=relative_path)
    except SyntaxError as error:
        record.parse_error = f"{error.msg} (line {error.lineno}, column {error.offset})"
        return record
    visitor = _IndexVisitor()
    visitor.visit(tree)
    record.imports = visitor.imports
    record.symbols = visitor.symbols
    return record


def build_repository_index(repository: Path, exclusions: list[str] | None = None) -> IndexBuildResult:
    repository = repository.resolve()
    cache = repository / ".repopilot" / "index.json"
    warnings = []
    previous_files: dict[str, FileRecord] = {}
    if cache.is_file():
        try:
            previous = RepositoryIndex.model_validate_json(cache.read_text())
            if previous.version != _INDEX_VERSION:
                raise ValueError("Incompatible index version")
            previous_files = {file.path: file for file in previous.files}
        except ValueError:
            warnings.append("Ignoring corrupt or incompatible index cache")

    files = []
    indexed_files = 0
    reused_files = 0
    for path in iter_python_files(repository, exclusions):
        relative_path = normalize_repo_path(repository, path)
        content_hash = hashlib.sha256(path.read_text().encode()).hexdigest()
        if relative_path in previous_files and previous_files[relative_path].content_hash == content_hash:
            files.append(previous_files[relative_path])
            reused_files += 1
        else:
            files.append(index_python_file(repository, path))
            indexed_files += 1

    index = RepositoryIndex(version=_INDEX_VERSION, files=files)
    cache.parent.mkdir(exist_ok=True)
    cache.write_text(index.model_dump_json(indent=2) + "\n")
    return IndexBuildResult(
        index=index,
        indexed_files=indexed_files,
        reused_files=reused_files,
        warnings=warnings,
    )
