from pydantic import BaseModel

from minisweagent.repopilot.index import FileRecord, RepositoryIndex, SourceSpan
from minisweagent.repopilot.retrieval import RetrievalResult


class ContextExcerpt(BaseModel):
    path: str
    span: SourceSpan
    content: str
    score: float
    reasons: list[str]


class ContextPack(BaseModel):
    text: str
    excerpts: list[ContextExcerpt]
    excluded_paths: list[str]
    used_chars: int
    budget_chars: int


def _merge_spans(spans: list[SourceSpan]) -> list[SourceSpan]:
    merged = []
    for span in sorted(spans, key=lambda item: (item.start_line, item.end_line)):
        if merged and span.start_line <= merged[-1].end_line:
            merged[-1].end_line = max(merged[-1].end_line, span.end_line)
        else:
            merged.append(span.model_copy())
    return merged


def _candidate_spans(file: FileRecord, result: RetrievalResult) -> list[SourceSpan]:
    matched = {term.casefold() for term in result.matched_terms}
    spans = [
        symbol.span
        for symbol in file.symbols
        if symbol.name.casefold() in matched or symbol.qualified_name.casefold() in matched
    ]
    if spans:
        return _merge_spans(spans)
    return [SourceSpan(start_line=1, end_line=max(1, len(file.source.splitlines())))]


def _render(excerpt: ContextExcerpt) -> str:
    return f"### {excerpt.path}:{excerpt.span.start_line}-{excerpt.span.end_line}\n{excerpt.content}"


def pack_context(
    index: RepositoryIndex,
    results: list[RetrievalResult],
    budget_chars: int,
) -> ContextPack:
    files = {file.path: file for file in index.files}
    excerpts = []
    excluded_paths = []
    rendered = []
    for result in results:
        file = files[result.path]
        lines = file.source.splitlines()
        for span in _candidate_spans(file, result):
            bounded_span = SourceSpan(
                start_line=max(1, span.start_line),
                end_line=min(len(lines), span.end_line),
            )
            excerpt = ContextExcerpt(
                path=file.path,
                span=bounded_span,
                content="\n".join(lines[bounded_span.start_line - 1 : bounded_span.end_line]),
                score=result.score,
                reasons=[name for name, score in result.score_breakdown.items() if score > 0],
            )
            candidate = _render(excerpt)
            separator = "\n\n" if rendered else ""
            if len("".join(rendered)) + len(separator) + len(candidate) <= budget_chars:
                rendered.extend([separator, candidate])
                excerpts.append(excerpt)
            elif file.path not in excluded_paths:
                excluded_paths.append(file.path)
    text = "".join(rendered)
    return ContextPack(
        text=text,
        excerpts=excerpts,
        excluded_paths=excluded_paths,
        used_chars=len(text),
        budget_chars=budget_chars,
    )
