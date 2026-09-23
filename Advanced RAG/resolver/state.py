from typing import Any
from typing_extensions import TypedDict


class ResolverState(TypedDict):
    query: str
    normalized_query: str
    entities: list[str]
    error_codes: list[str]
    technology: list[str]
    intent: str

    retrieved_chunks: list[dict[str, Any]]
    reranked_chunks: list[dict[str, Any]]

    relevant_tickets: list[str]

    evidence: list[dict[str, Any]]

    solution: str
    next_steps: list[str]

    confidence: float
    status: str

    request_id: str