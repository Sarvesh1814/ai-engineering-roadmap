from typing import Any
from dataclasses import dataclass

from config.settings import get_settings
from embeddings.factory import get_embedding_model
from vectorstore.qdrant import QdrantVectorStore


@dataclass
class DenseRetrievalResult:
    id: str
    score: float
    payload: dict[str, Any]


class DenseRetriever:
    def __init__(self):
        settings = get_settings()
        self.embedding_model = get_embedding_model(settings.embedding_model)
        self.vector_store = QdrantVectorStore()
        self.top_k = settings.retrieval_dense_top_k

    def connect(self) -> None:
        self.vector_store.connect()

    def search(self, query: str, filter_: dict | None = None) -> list[DenseRetrievalResult]:
        query_vector = self.embedding_model.embed(query)

        from qdrant_client.models import Filter, FieldCondition, MatchValue
        qdrant_filter = None
        if filter_:
            conditions = []
            for key, value in filter_.items():
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
            qdrant_filter = Filter(must=conditions)

        results = self.vector_store.search(
            vector=query_vector,
            top_k=self.top_k,
            filter_=qdrant_filter,
        )

        return [
            DenseRetrievalResult(
                id=hit["id"],
                score=hit["score"],
                payload=hit["payload"],
            )
            for hit in results
        ]

    def search_by_vector(self, vector: list[float], filter_: dict | None = None, top_k: int | None = None) -> list[DenseRetrievalResult]:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        qdrant_filter = None
        if filter_:
            conditions = []
            for key, value in filter_.items():
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
            qdrant_filter = Filter(must=conditions)

        k = top_k or self.top_k
        results = self.vector_store.search(
            vector=vector,
            top_k=k,
            filter_=qdrant_filter,
        )

        return [
            DenseRetrievalResult(
                id=hit["id"],
                score=hit["score"],
                payload=hit["payload"],
            )
            for hit in results
        ]