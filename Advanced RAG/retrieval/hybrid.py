from typing import Any
from dataclasses import dataclass
from collections import defaultdict

from retrieval.dense import DenseRetriever, DenseRetrievalResult
from retrieval.sparse import BM25Retriever, SparseRetrievalResult
from config.settings import get_settings


@dataclass
class HybridRetrievalResult:
    id: str
    score: float
    payload: dict[str, Any]
    dense_score: float | None = None
    sparse_score: float | None = None


class HybridRetriever:
    def __init__(self):
        settings = get_settings()
        self.dense_retriever = DenseRetriever()
        self.sparse_retriever = BM25Retriever()
        self.dense_top_k = settings.retrieval_dense_top_k
        self.sparse_top_k = settings.retrieval_sparse_top_k
        self.rrf_k = 60

    def connect(self) -> None:
        self.dense_retriever.connect()
        self.sparse_retriever.connect()

    def search(self, query: str, filter_: dict | None = None) -> list[HybridRetrievalResult]:
        dense_results = self.dense_retriever.search(query, filter_)
        sparse_results = self.sparse_retriever.search(query, filter_)

        return self._rrf_fusion(dense_results, sparse_results)

    def _rrf_fusion(
        self,
        dense_results: list[DenseRetrievalResult],
        sparse_results: list[SparseRetrievalResult],
    ) -> list[HybridRetrievalResult]:
        dense_rank = {r.id: i + 1 for i, r in enumerate(dense_results)}
        sparse_rank = {r.id: i + 1 for i, r in enumerate(sparse_results)}

        all_ids = set(dense_rank.keys()) | set(sparse_rank.keys())

        fused_scores = {}
        for doc_id in all_ids:
            dense_r = dense_rank.get(doc_id, len(dense_results) + 1)
            sparse_r = sparse_rank.get(doc_id, len(sparse_results) + 1)

            rrf_score = (1.0 / (self.rrf_k + dense_r)) + (1.0 / (self.rrf_k + sparse_r))
            fused_scores[doc_id] = rrf_score

        sorted_ids = sorted(fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True)

        dense_map = {r.id: r for r in dense_results}
        sparse_map = {r.id: r for r in sparse_results}

        results = []
        for doc_id in sorted_ids:
            dense_hit = dense_map.get(doc_id)
            sparse_hit = sparse_map.get(doc_id)

            payload = dense_hit.payload if dense_hit else (sparse_hit.payload if sparse_hit else {})

            results.append(HybridRetrievalResult(
                id=doc_id,
                score=fused_scores[doc_id],
                payload=payload,
                dense_score=dense_hit.score if dense_hit else None,
                sparse_score=sparse_hit.score if sparse_hit else None,
            ))

        return results