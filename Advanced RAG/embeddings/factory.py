from embeddings.bge import BGEEmbedding


def get_embedding_model(model_name: str):

    # As of now, we only support BGE embeddings. You can add more embedding models in the future.

    model_name = model_name.strip()

    # Supports all BAAI BGE models
    if model_name.lower().startswith("baai/bge"):
        return BGEEmbedding(model_name=model_name)

    """
    # For future use, you can add more embedding models here.    
    if model_name == "openai":
    return OpenAIEmbedding()

    if model_name == "voyage":
        return VoyageEmbedding()

    if model_name == "jina":
        return JinaEmbedding()
    
    """
    raise ValueError(f"Unsupported embedding model: {model_name}")
