from embeddings.bge import BGEEmbedding
from embeddings.base import EmbeddingModel

from config.settings import get_settings


def get_embedding_model(model_name: str | None = None) -> EmbeddingModel:
    settings = get_settings()
    name = (model_name or settings.embedding_model).strip()

    if name.lower().startswith("baai/bge"):
        return BGEEmbedding(model_name=name)

    raise ValueError(f"Unsupported embedding model: {name}")