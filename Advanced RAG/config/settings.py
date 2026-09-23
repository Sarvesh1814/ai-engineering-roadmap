import os
from pathlib import Path
from typing import Any, Optional
import yaml
from dotenv import load_dotenv

load_dotenv()

_CONFIG: Optional[dict] = None


def _load_config() -> dict:
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG

    config_path = Path(__file__).parent / "settings.yaml"
    with config_path.open("r") as f:
        _CONFIG = yaml.safe_load(f)

    _apply_env_overrides(_CONFIG)
    return _CONFIG


def _apply_env_overrides(config: dict, prefix: str = "") -> None:
    for key, value in config.items():
        full_key = f"{prefix}{key}".upper()
        env_key = full_key.replace(".", "_")

        if isinstance(value, dict):
            _apply_env_overrides(value, f"{prefix}{key}.")
        else:
            env_value = os.getenv(env_key)
            if env_value is not None:
                config[key] = _convert_type(env_value, type(value))


def _convert_type(value: str, target_type: type) -> Any:
    if target_type == bool:
        return value.lower() in ("true", "1", "yes", "on")
    if target_type == int:
        return int(value)
    if target_type == float:
        return float(value)
    return value


def get_config() -> dict:
    return _load_config()


def get(key: str, default: Any = None) -> Any:
    config = _load_config()
    keys = key.split(".")
    value = config
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    return value


class Settings:
    app_env: str = "development"
    log_level: str = "INFO"

    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_database: str = "servicenow"
    mysql_user: str = "rag_user"
    mysql_password: str = ""
    mysql_ingestion_view: str = "vw_ops_workitem_ingestion"
    mysql_resolver_view: str = "vw_ops_workitem_flat"
    mysql_batch_size: int = 1000

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "service_now_knowledge"
    qdrant_vector_size: int = 1024
    qdrant_distance: str = "COSINE"

    embedding_provider: str = "bge"
    embedding_model: str = "BAAI/bge-large-en-v1.5"
    embedding_normalize: bool = True
    embedding_batch_size: int = 32

    llm_provider: str = "ollama"
    llm_model_name: str = "devstral"
    llm_base_url: str = "http://localhost:11434"
    llm_api_key: str = ""
    llm_temperature: float = 0.1

    reranker_model: str = "BAAI/bge-reranker-base"

    retrieval_dense_top_k: int = 50
    retrieval_sparse_top_k: int = 50
    retrieval_rerank_top_k: int = 10
    retrieval_final_ticket_count: int = 5

    chunking_chunk_size: int = 450
    chunking_chunk_overlap: int = 60
    chunking_min_chunk_size: int = 100

    ingestion_mysql_batch_size: int = 1000
    ingestion_embedding_batch_size: int = 32
    ingestion_checkpoint_file: str = ".ingestion_checkpoint"
    ingestion_failure_log: str = ".ingestion_failures.jsonl"
    bm25_index_path: str = ".bm25_index.json"
    ingestion_knowledge_version: int = 1

    def __init__(self):
        config = _load_config()
        self._load_from_config(config)

    def _load_from_config(self, config: dict) -> None:
        self.app_env = config.get("app", {}).get("env", self.app_env)
        self.log_level = config.get("app", {}).get("log_level", self.log_level)

        mysql = config.get("mysql", {})
        self.mysql_host = mysql.get("host", self.mysql_host)
        self.mysql_port = mysql.get("port", self.mysql_port)
        self.mysql_database = mysql.get("database", self.mysql_database)
        self.mysql_user = mysql.get("user", self.mysql_user)
        self.mysql_password = mysql.get("password", self.mysql_password) or os.getenv("MYSQL_PASSWORD", "")
        self.mysql_ingestion_view = mysql.get("ingestion_view", self.mysql_ingestion_view)
        self.mysql_resolver_view = mysql.get("resolver_view", self.mysql_resolver_view)
        self.mysql_batch_size = mysql.get("batch_size", self.mysql_batch_size)

        qdrant = config.get("qdrant", {})
        self.qdrant_host = qdrant.get("host", self.qdrant_host)
        self.qdrant_port = qdrant.get("port", self.qdrant_port)
        self.qdrant_collection = qdrant.get("collection", self.qdrant_collection)
        self.qdrant_vector_size = qdrant.get("vector_size", self.qdrant_vector_size)
        self.qdrant_distance = qdrant.get("distance", self.qdrant_distance)

        embedding = config.get("embedding", {})
        self.embedding_provider = embedding.get("provider", self.embedding_provider)
        self.embedding_model = embedding.get("model", self.embedding_model)
        self.embedding_normalize = embedding.get("normalize", self.embedding_normalize)
        self.embedding_batch_size = embedding.get("batch_size", self.embedding_batch_size)

        llm = config.get("llm", {})
        self.llm_provider = llm.get("provider", self.llm_provider)
        self.llm_model_name = llm.get("model_name", self.llm_model_name)
        self.llm_base_url = llm.get("base_url", self.llm_base_url)
        self.llm_api_key = llm.get("api_key", self.llm_api_key) or os.getenv("API_KEY", "")
        self.llm_temperature = llm.get("temperature", self.llm_temperature)

        reranker = config.get("reranker", {})
        self.reranker_model = reranker.get("model", self.reranker_model)

        retrieval = config.get("retrieval", {})
        self.retrieval_dense_top_k = retrieval.get("dense_top_k", self.retrieval_dense_top_k)
        self.retrieval_sparse_top_k = retrieval.get("sparse_top_k", self.retrieval_sparse_top_k)
        self.retrieval_rerank_top_k = retrieval.get("rerank_top_k", self.retrieval_rerank_top_k)
        self.retrieval_final_ticket_count = retrieval.get("final_ticket_count", self.retrieval_final_ticket_count)

        chunking = config.get("chunking", {})
        self.chunking_chunk_size = chunking.get("chunk_size", self.chunking_chunk_size)
        self.chunking_chunk_overlap = chunking.get("chunk_overlap", self.chunking_chunk_overlap)
        self.chunking_min_chunk_size = chunking.get("min_chunk_size", self.chunking_min_chunk_size)

        ingestion = config.get("ingestion", {})
        self.ingestion_mysql_batch_size = ingestion.get("mysql_batch_size", self.ingestion_mysql_batch_size)
        self.ingestion_embedding_batch_size = ingestion.get("embedding_batch_size", self.ingestion_embedding_batch_size)
        self.ingestion_checkpoint_file = ingestion.get("checkpoint_file", self.ingestion_checkpoint_file)
        self.ingestion_failure_log = ingestion.get("failure_log", self.ingestion_failure_log)
        self.bm25_index_path = ingestion.get("bm25_index_path", self.bm25_index_path)
        self.ingestion_knowledge_version = ingestion.get("knowledge_version", self.ingestion_knowledge_version)


_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance