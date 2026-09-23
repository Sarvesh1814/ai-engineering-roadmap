from typing import Any
from dataclasses import dataclass

from sentence_transformers import CrossEncoder

from config.settings import get_settings
from retrieval.hybrid import HybridRetrievalResult


@dataclass
class RerankedResult:
    id: str
    score: float
    payload: dict[str, Any]
    dense_score: float | None = None
    sparse_score: float | None = None
    rerank_score: float | None = None


class Reranker:
    def __init__(self):
        settings = get_settings()
        self.model = CrossEncoder(settings.reranker_model)
        self.top_k = settings.retrieval_rerank_top_k

    def rerank(self, query: str, results: list[HybridRetrievalResult]) -> list[RerankedResult]:
        if not results:
            return []

        pairs = [(query, result.payload.get("text", "")) for result in results]
        scores = self.model.predict(pairs)

        reranked = []
        for result, score in zip(results, scores):
            reranked.append(RerankedResult(
                id=result.id,
                score=float(score),
                payload=result.payload,
                dense_score=result.dense_score,
                sparse_score=result.sparse_score,
                rerank_score=float(score),
            ))

        reranked.sort(key=lambda r: r.score, reverse=True)
        return reranked[:self.top_k]