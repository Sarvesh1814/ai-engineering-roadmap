import json
from pathlib import Path
from typing import Any
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from config.settings import get_settings
from vectorstore.qdrant import QdrantVectorStore


@dataclass
class SparseRetrievalResult:
    id: str
    score: float
    payload: dict[str, Any]


class BM25Retriever:
    """
    BM25 sparse retriever backed by a persisted index.

    Payloads are cached alongside the BM25 corpus at build/save time so that
    search() never issues any Qdrant calls per result — the old code made one
    unfiltered scroll() call *per candidate document*, which was O(n) network
    round-trips per query.
    """

    def __init__(self):
        settings = get_settings()
        self.vector_store = QdrantVectorStore()
        self.top_k = settings.retrieval_sparse_top_k
        self._corpus: list[list[str]] = []
        self._corpus_ids: list[str] = []
        self._corpus_payloads: list[dict[str, Any]] = []
        self._bm25: BM25Okapi | None = None
        self._index_path = Path(settings.bm25_index_path) if hasattr(settings, "bm25_index_path") else Path(".bm25_index.json")

    def connect(self) -> None:
        self.vector_store.connect()
        self._load_or_build_index()

    def _load_or_build_index(self) -> None:
        if self._index_path.exists():
            self._load_index()
        else:
            self._build_index()
            self._save_index()

    def _build_index(self) -> None:
        """Build BM25 index from all Qdrant vectors, paginating to handle large collections."""
        results = self.vector_store.scroll_all()
        self._corpus = []
        self._corpus_ids = []
        self._corpus_payloads = []

        for hit in results:
            text = hit["payload"].get("text", "")
            if text:
                tokens = text.lower().split()
                self._corpus.append(tokens)
                self._corpus_ids.append(hit["id"])
                self._corpus_payloads.append(hit["payload"])

        if self._corpus:
            self._bm25 = BM25Okapi(self._corpus)

    def _save_index(self) -> None:
        if self._bm25 and self._corpus:
            data = {
                "corpus": self._corpus,
                "corpus_ids": self._corpus_ids,
                "corpus_payloads": self._corpus_payloads,
            }
            with self._index_path.open("w") as f:
                json.dump(data, f)

    def _load_index(self) -> None:
        with self._index_path.open("r") as f:
            data = json.load(f)
        self._corpus = data["corpus"]
        self._corpus_ids = data["corpus_ids"]
        # Gracefully handle old index files that predate payload caching
        self._corpus_payloads = data.get("corpus_payloads", [{} for _ in self._corpus_ids])
        self._bm25 = BM25Okapi(self._corpus)

    def search(self, query: str, filter_: dict | None = None) -> list[SparseRetrievalResult]:
        if not self._bm25 or not self._corpus:
            return []

        query_tokens = query.lower().split()
        scores = self._bm25.get_scores(query_tokens)

        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[: self.top_k * 2]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                # Payload is already cached in the index — no Qdrant call needed
                results.append(
                    SparseRetrievalResult(
                        id=self._corpus_ids[idx],
                        score=float(scores[idx]),
                        payload=self._corpus_payloads[idx],
                    )
                )

        if filter_:
            filtered = []
            for r in results:
                match = True
                for key, value in filter_.items():
                    if r.payload.get(key) != value:
                        match = False
                        break
                if match:
                    filtered.append(r)
            results = filtered

        return results[: self.top_k]

    def rebuild_index(self) -> None:
        self._build_index()
        self._save_index()