import math
import re
from collections import Counter

from pydantic import BaseModel

from minisweagent.repopilot.index import FileRecord, RepositoryIndex
from minisweagent.repopilot.task_analysis import TaskAnalysis


class RetrievalResult(BaseModel):
    path: str
    score: float
    score_breakdown: dict[str, float]
    matched_terms: list[str]


_QUERY_STOP_TOKENS = {"py", "src", "test", "tests"}


def _tokens(value: str) -> list[str]:
    result = []
    for token in re.findall(r"[A-Za-z][A-Za-z0-9_]*", value):
        lowered = token.casefold()
        result.append(lowered)
        result.extend(part for part in lowered.split("_") if part != lowered)
    return result


def _weighted_terms(file: FileRecord) -> Counter[str]:
    terms: Counter[str] = Counter()
    terms.update({token: 2.0 for token in _tokens(file.path)})
    for symbol in file.symbols:
        terms.update({token: 3.0 for token in _tokens(f"{symbol.qualified_name} {symbol.signature}")})
        terms.update({token: 1.5 for token in _tokens(symbol.docstring or "")})
    terms.update({token: count * 0.5 for token, count in Counter(_tokens(file.source)).items()})
    return terms


def retrieve(index: RepositoryIndex, analysis: TaskAnalysis, limit: int = 5) -> list[RetrievalResult]:
    query_terms = [term for term in _tokens(" ".join(analysis.search_terms)) if term not in _QUERY_STOP_TOKENS]
    documents = [_weighted_terms(file) for file in index.files]
    if not documents or not query_terms:
        return []
    average_length = sum(sum(document.values()) for document in documents) / len(documents)
    document_frequency = {
        term: sum(term in document for document in documents)
        for term in set(query_terms)
    }
    results = []
    for file, document in zip(index.files, documents):
        length = sum(document.values())
        lexical = 0.0
        for term in query_terms:
            frequency = document[term]
            if not frequency:
                continue
            inverse_frequency = math.log(1 + (len(documents) - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
            lexical += inverse_frequency * (frequency * 2.5) / (
                frequency + 1.5 * (0.25 + 0.75 * length / average_length)
            )
        normalized_symbols = {
            name.casefold()
            for symbol in file.symbols
            for name in (symbol.name, symbol.qualified_name)
        }
        exact_symbol = 6.0 * sum(identifier.casefold() in normalized_symbols for identifier in analysis.identifiers)
        exact_path = 8.0 * sum(
            file.path.casefold() == path.casefold() or file.path.casefold().endswith(f"/{path.casefold()}")
            for path in analysis.paths
        )
        matched_terms = [
            term
            for term in analysis.search_terms
            if set(_tokens(term)).intersection(document)
            or term.casefold() in normalized_symbols
            or file.path.casefold() == term.casefold()
        ]
        score = lexical + exact_symbol + exact_path
        if score > 0:
            results.append(
                RetrievalResult(
                    path=file.path,
                    score=score,
                    score_breakdown={
                        "lexical": lexical,
                        "exact_symbol": exact_symbol,
                        "exact_path": exact_path,
                        "dependency": 0.0,
                    },
                    matched_terms=matched_terms,
                )
            )
    ranked = sorted(results, key=lambda result: (-result.score, result.path))
    result_by_path = {result.path: result for result in ranked}
    file_by_path = {file.path: file for file in index.files}
    file_by_module = {file.module: file for file in index.files}
    for seed in ranked[:3]:
        for imported in file_by_path[seed.path].imports:
            if imported.module not in file_by_module:
                continue
            dependency = file_by_module[imported.module]
            dependency_score = seed.score * 0.25
            if dependency.path in result_by_path:
                result = result_by_path[dependency.path]
                result.score += dependency_score
                result.score_breakdown["dependency"] += dependency_score
            else:
                result_by_path[dependency.path] = RetrievalResult(
                    path=dependency.path,
                    score=dependency_score,
                    score_breakdown={
                        "lexical": 0.0,
                        "exact_symbol": 0.0,
                        "exact_path": 0.0,
                        "dependency": dependency_score,
                    },
                    matched_terms=[],
                )
    return sorted(result_by_path.values(), key=lambda result: (-result.score, result.path))[:limit]
