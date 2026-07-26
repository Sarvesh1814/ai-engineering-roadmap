from sentence_transformers import SentenceTransformer

from embeddings.base import EmbeddingModel
import os


class BGEEmbedding(EmbeddingModel):

    def __init__(self,model_name: str = "BAAI/bge-large-en-v1.5"):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> list[float]:
        return self.model.encode(
            text,
            normalize_embeddings=True
        ).tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(
            texts,
            normalize_embeddings=True
        ).tolist()