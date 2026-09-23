from typing import Any
from dataclasses import dataclass
from collections import defaultdict

from config import get_settings, get_logger
from retrieval.hybrid import HybridRetriever, HybridRetrievalResult


@dataclass
class RetrievedTicket:
    ticket_id: str
    score: float
    chunks: list[HybridRetrievalResult]
    problem: str | None = None
    root_cause: str | None = None
    resolution: str | None = None
    next_steps: list[str] | None = None


@dataclass
class RetrievalResponse:
    tickets: list[RetrievedTicket]
    total_chunks_retrieved: int
    reranked_chunks: int


class Retriever:
    """
    Performs hybrid (dense + BM25) retrieval and groups results by ticket.
    Reranking is intentionally NOT performed here — it is a separate graph
    node in the resolver pipeline so it can be timed and controlled independently.
    """

    def __init__(self):
        settings = get_settings()
        self.hybrid_retriever = HybridRetriever()
        self.final_ticket_count = settings.retrieval_final_ticket_count
        self.logger = get_logger("retriever")

    def connect(self) -> None:
        try:
            self.hybrid_retriever.connect()
            self.logger.info("Retriever connected successfully")
        except Exception as e:
            self.logger.error("Failed to connect retriever", extra={"metadata": {"error": str(e), "error_type": type(e).__name__}})
            raise

    def retrieve(self, query: str, filter_: dict | None = None) -> RetrievalResponse:
        try:
            hybrid_results = self.hybrid_retriever.search(query, filter_)
            self.logger.debug(f"Dense+sparse search returned {len(hybrid_results)} results")

            tickets_map = self._group_by_ticket(hybrid_results)
            ranked_tickets = self._rank_tickets(tickets_map)
            final_tickets = ranked_tickets[:self.final_ticket_count]

            self.logger.info(
                f"Retrieval complete: {len(final_tickets)} tickets, {len(hybrid_results)} chunks",
            )
            return RetrievalResponse(
                tickets=final_tickets,
                total_chunks_retrieved=len(hybrid_results),
                reranked_chunks=0,  # Reranking not done here
            )
        except Exception as e:
            self.logger.error(
                "Retrieval failed",
                extra={"metadata": {"query": query[:100], "filter": filter_, "error": str(e), "error_type": type(e).__name__}},
            )
            raise

    def _group_by_ticket(self, results: list[HybridRetrievalResult]) -> dict[str, list[HybridRetrievalResult]]:
        grouped: dict[str, list[HybridRetrievalResult]] = defaultdict(list)
        for result in results:
            ticket_id = result.payload.get("ticket_id", "unknown")
            grouped[ticket_id].append(result)
        return grouped

    def _rank_tickets(self, tickets_map: dict[str, list[HybridRetrievalResult]]) -> list[RetrievedTicket]:
        ranked = []
        for ticket_id, chunks in tickets_map.items():
            best_score = max(chunk.score for chunk in chunks)

            problem = None
            root_cause = None
            resolution = None
            next_steps = None

            for chunk in chunks:
                if chunk.payload.get("chunk_type") == "problem" and not problem:
                    problem = chunk.payload.get("problem")
                if chunk.payload.get("chunk_type") == "root_cause" and not root_cause:
                    root_cause = chunk.payload.get("root_cause")
                if chunk.payload.get("chunk_type") == "resolution" and not resolution:
                    resolution = chunk.payload.get("resolution")
                if chunk.payload.get("chunk_type") == "next_steps" and not next_steps:
                    next_steps = chunk.payload.get("next_steps")

            ranked.append(RetrievedTicket(
                ticket_id=ticket_id,
                score=best_score,
                chunks=chunks,
                problem=problem,
                root_cause=root_cause,
                resolution=resolution,
                next_steps=next_steps,
            ))

        ranked.sort(key=lambda t: t.score, reverse=True)
        return ranked