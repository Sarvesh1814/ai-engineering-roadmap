from dataclasses import dataclass
from typing import Any

from config import get_settings
from config.logging import get_logger
from embeddings.factory import get_embedding_model
from config.llm import get_llm


@dataclass
class HealthStatus:
    healthy: bool
    service: str
    message: str
    details: dict[str, Any] = None


class HealthChecker:
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger("health")

    def check_qdrant(self) -> HealthStatus:
        from vectorstore.qdrant import QdrantVectorStore
        try:
            store = QdrantVectorStore()
            store.connect()
            info = store.get_collection_info()
            return HealthStatus(
                healthy=True,
                service="qdrant",
                message="Qdrant connection successful",
                details={"collection": info},
            )
        except Exception as e:
            return HealthStatus(
                healthy=False,
                service="qdrant",
                message=f"Qdrant connection failed: {e}",
            )

    def check_mysql(self) -> HealthStatus:
        try:
            from ingestion.mysql_loader import load_view
            df_iter = load_view(self.settings.mysql_ingestion_view, chunk_size=1)
            next(df_iter)
            return HealthStatus(
                healthy=True,
                service="mysql",
                message="MySQL connection successful",
            )
        except Exception as e:
            return HealthStatus(
                healthy=False,
                service="mysql",
                message=f"MySQL connection failed: {e}",
            )

    def check_embedding_model(self) -> HealthStatus:
        try:
            model = get_embedding_model(self.settings.embedding_model)
            _ = model.embed("health check")
            return HealthStatus(
                healthy=True,
                service="embedding_model",
                message="Embedding model loaded successfully",
            )
        except Exception as e:
            return HealthStatus(
                healthy=False,
                service="embedding_model",
                message=f"Embedding model check failed: {e}",
            )

    def check_llm(self) -> HealthStatus:
        try:
            llm = get_llm()
            _ = llm.invoke("health check")
            return HealthStatus(
                healthy=True,
                service="llm",
                message="LLM connection successful",
            )
        except Exception as e:
            return HealthStatus(
                healthy=False,
                service="llm",
                message=f"LLM connection failed: {e}",
            )

    def check_all(self) -> dict[str, HealthStatus]:
        checks = {
            "qdrant": self.check_qdrant(),
            "mysql": self.check_mysql(),
            "embedding_model": self.check_embedding_model(),
            "llm": self.check_llm(),
        }
        return checks

    def readiness(self) -> tuple[bool, dict[str, HealthStatus]]:
        checks = self.check_all()
        all_healthy = all(c.healthy for c in checks.values())
        return all_healthy, checks

    def liveness(self) -> HealthStatus:
        return HealthStatus(
            healthy=True,
            service="application",
            message="Application is running",
        )