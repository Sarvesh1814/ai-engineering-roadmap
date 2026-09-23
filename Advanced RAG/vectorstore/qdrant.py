from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    PayloadSchemaType,
)

from config.settings import get_settings
from config.logging import get_logger


class QdrantVectorStore:

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        collection_name: str | None = None,
        vector_size: int | None = None,
    ):
        settings = get_settings()
        self.host = host or settings.qdrant_host
        self.port = port or settings.qdrant_port
        self.collection_name = collection_name or settings.qdrant_collection
        self.vector_size = vector_size or settings.qdrant_vector_size
        self.distance = Distance.COSINE
        self.client = None
        self.logger = get_logger("qdrant")

    def connect(self) -> None:
        try:
            self.logger.info(f"Connecting to Qdrant", extra={"metadata": {"host": self.host, "port": self.port}})
            self.client = QdrantClient(host=self.host, port=self.port)
            self.client.get_collections()
            self.logger.info("Connected to Qdrant successfully")
        except Exception as e:
            self.logger.error(
                "Failed to connect to Qdrant",
                extra={"metadata": {"host": self.host, "port": self.port, "error": str(e), "error_type": type(e).__name__}},
            )
            raise

    def create_collection(self) -> None:
        collections = [
            c.name for c in self.client.get_collections().collections
        ]

        if self.collection_name not in collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=self.distance,
                ),
            )
            self.logger.info("Collection created", extra={"metadata": {"collection": self.collection_name}})
        else:
            self.logger.info("Collection already exists", extra={"metadata": {"collection": self.collection_name}})

        self._create_payload_indexes()

    def _create_payload_indexes(self) -> None:
        index_fields = [
            "ticket_id",
            "ticket_type",
            "ticket_state",
            "category",
            "subcategory",
            "assignment_group",
            "chunk_type",
            "resolved_at",
            "knowledge_version",
        ]

        for field in index_fields:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field,
                    field_schema=PayloadSchemaType.KEYWORD,
                )
                self.logger.debug(f"Payload index created for {field}")
            except Exception as e:
                self.logger.debug(f"Payload index for {field} may already exist: {e}")

    def upsert(
        self,
        vectors: list[list[float]],
        payloads: list[dict],
        ids: list[str] | None = None,
    ) -> None:
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")

        if ids is None:
            ids = [str(i) for i in range(len(vectors))]

        points = [
            PointStruct(id=id_, vector=vector, payload=payload)
            for id_, vector, payload in zip(ids, vectors, payloads)
        ]

        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True,
            )
            self.logger.info(f"Upserted {len(points)} points", extra={"metadata": {"count": len(points), "collection": self.collection_name}})
        except Exception as e:
            self.logger.error("Failed to upsert points", extra={"metadata": {"count": len(points), "error": str(e)}})
            raise

    def delete_by_ticket(self, ticket_id: str) -> int:
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            result = self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="ticket_id",
                            match=MatchValue(value=ticket_id),
                        )
                    ]
                ),
                wait=True,
            )
            self.logger.info(f"Deleted chunks for ticket {ticket_id}", extra={"metadata": {"ticket_id": ticket_id, "status": getattr(result, "status", "completed")}})
            return 1
        except Exception as e:
            self.logger.error(f"Failed to delete chunks for ticket {ticket_id}", extra={"metadata": {"ticket_id": ticket_id, "error": str(e)}})
            raise

    def search(
        self,
        vector: list[float],
        top_k: int = 10,
        filter_: Filter | None = None,
    ) -> list[dict]:
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=top_k,
                query_filter=filter_,
                with_payload=True,
                with_vectors=False,
            )

            return [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload,
                }
                for hit in results
            ]
        except Exception as e:
            self.logger.error("Qdrant search failed", extra={"metadata": {"top_k": top_k, "error": str(e), "error_type": type(e).__name__}})
            raise

    def scroll(
        self,
        filter_: Filter | None = None,
        limit: int = 100,
    ) -> list[dict]:
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")

        results, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=filter_,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        return [
            {
                "id": hit.id,
                "payload": hit.payload,
            }
            for hit in results
        ]

    def scroll_all(
        self,
        filter_: Filter | None = None,
        page_size: int = 1000,
    ) -> list[dict]:
        """
        Scroll all records from the collection using Qdrant's cursor-based pagination.

        Unlike scroll(), this method fetches every record regardless of collection size.
        Use this instead of scroll(limit=N) whenever the full corpus is needed (e.g.,
        BM25 index build) to avoid silently truncating large collections.
        """
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")

        all_results = []
        offset = None

        while True:
            batch, next_offset = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=filter_,
                limit=page_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            all_results.extend(
                {"id": hit.id, "payload": hit.payload}
                for hit in batch
            )

            if next_offset is None:
                break
            offset = next_offset

        self.logger.debug(
            "scroll_all complete",
            extra={"metadata": {"total_records": len(all_results), "collection": self.collection_name}},
        )
        return all_results

    def get_collection_info(self) -> dict:
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")

        info = self.client.get_collection(self.collection_name)
        return {
            "name": self.collection_name,  # Fixed: was incorrectly set to vector size
            "vector_size": info.config.params.vectors.size,
            "distance": info.config.params.vectors.distance.value,
            "points_count": info.points_count,
            "status": info.status.value,
        }