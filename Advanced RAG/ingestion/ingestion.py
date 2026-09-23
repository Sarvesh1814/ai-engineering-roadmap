import json
import os
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INGESTION_DIR = Path(__file__).resolve().parent

for path in [PROJECT_ROOT, INGESTION_DIR]:
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from config import get_llm, get_settings, get_logger
from config.metrics import (
    ingestion_tickets_processed,
    ingestion_tickets_failed,
    ingestion_chunks_created,
    ingestion_embeddings_created,
    ingestion_qdrant_upserts,
    ingestion_latency,
)
from embeddings.factory import get_embedding_model
from ingestion.chunking import TicketAwareChunker
from ingestion.mysql_loader import load_view
from ingestion.preprocessing import TicketKnowledgeExtractor
from vectorstore.qdrant import QdrantVectorStore


class IngestionPipeline:
    def __init__(self):
        settings = get_settings()
        self.logger = get_logger("ingestion")
        self.llm = get_llm()
        self.extractor = TicketKnowledgeExtractor(self.llm)
        self.chunker = TicketAwareChunker()
        self.embedding_model = get_embedding_model(settings.embedding_model)
        self.vector_store = QdrantVectorStore()
        self.checkpoint_file = Path(settings.ingestion_checkpoint_file)
        self.failure_log = Path(settings.ingestion_failure_log)
        self.embedding_batch_size = settings.ingestion_embedding_batch_size

    def run(self, incremental: bool = True) -> dict:
        """
        Run the full ingestion pipeline.

        Args:
            incremental: If True, only process tickets updated since last checkpoint

        Returns:
            Dictionary with ingestion statistics
        """
        start_time = time.perf_counter()
        self.vector_store.connect()
        self.vector_store.create_collection()

        last_checkpoint = self._load_checkpoint() if incremental else None
        stats = {
            "tickets_processed": 0,
            "chunks_created": 0,
            "vectors_upserted": 0,
            "tickets_skipped": 0,
            "failures": 0,
        }

        view_name = get_settings().mysql_ingestion_view
        batch_size = get_settings().mysql_batch_size

        if incremental and last_checkpoint:
            self.logger.info(f"Incremental mode: loading tickets updated since {last_checkpoint}")
            df_iterator = self._load_incremental(view_name, batch_size, last_checkpoint)
        else:
            self.logger.info("Full ingestion mode")
            df_iterator = load_view(view_name, batch_size)

        max_updated_at = None

        for chunk_no, df in enumerate(df_iterator, start=1):
            self.logger.info(f"Processing batch {chunk_no}", extra={"metadata": {"row_count": len(df)}})

            for _, row in df.iterrows():
                ticket_data = self._normalize_ticket(row.to_dict())

                if incremental and last_checkpoint:
                    updated_at = ticket_data.get("updated_at")
                    if updated_at is not None:
                        # Normalize to ISO 8601 string for safe comparison.
                        # pandas returns datetime/Timestamp objects; str() format
                        # varies, so isoformat() is used for reliable ordering.
                        updated_at_str = (
                            updated_at.isoformat()
                            if hasattr(updated_at, "isoformat")
                            else str(updated_at)
                        )
                        if updated_at_str <= last_checkpoint:
                            continue
                        if max_updated_at is None or updated_at_str > max_updated_at:
                            max_updated_at = updated_at_str

                try:
                    self._process_ticket(ticket_data, stats)
                except Exception as e:
                    stats["failures"] += 1
                    ingestion_tickets_failed.inc()
                    self._log_failure(ticket_data, e)
                    self.logger.error(
                        f"Failed to process ticket {ticket_data.get('ticket_id', 'unknown')}",
                        extra={"metadata": {"error": str(e)}},
                    )

            if max_updated_at:
                self._save_checkpoint(max_updated_at)

        elapsed = time.perf_counter() - start_time
        ingestion_latency.observe(elapsed)
        self.logger.info(f"Ingestion complete", extra={"metadata": {**stats, "duration_seconds": elapsed}})
        return stats

    def _normalize_ticket(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Normalize field names from ServiceNow views to ingestion schema."""
        data = dict(raw)

        # Ticket identifier: prefer display_id (e.g. INC0010749), then id
        if not data.get("ticket_id"):
            data["ticket_id"] = data.get("display_id") or (str(data.get("id")) if data.get("id") is not None else None)

        # State & Type mapping
        if not data.get("ticket_state"):
            data["ticket_state"] = data.get("state", "")
        if not data.get("ticket_type"):
            data["ticket_type"] = data.get("type", "")

        # Priority & Resolution code
        if not data.get("priority"):
            data["priority"] = data.get("Priority", "")
        if not data.get("resolution_code"):
            data["resolution_code"] = data.get("Close_Code", "")

        # Timestamps
        if not data.get("created_at"):
            data["created_at"] = data.get("created_time", "")
        if not data.get("resolved_at"):
            data["resolved_at"] = data.get("RCA_Date") or data.get("modified_time", "")
        if not data.get("updated_at"):
            data["updated_at"] = (
                data.get("updated_time")
                or data.get("modified_time")
                or data.get("OH_last_update")
            )

        # Comments fallback if comments field is empty or whitespace
        comments = data.get("comments")
        if not comments or not str(comments).strip():
            parts = []
            if data.get("title"):
                parts.append(f"Title: {data.get('title')}")
            if data.get("ticket_summary"):
                parts.append(f"Summary: {data.get('ticket_summary')}")
            if data.get("RCA"):
                parts.append(f"Root Cause Analysis: {data.get('RCA')}")
            if data.get("Resolution_Steps"):
                parts.append(f"Resolution Steps: {data.get('Resolution_Steps')}")
            if data.get("Close_Notes"):
                parts.append(f"Close Notes: {data.get('Close_Notes')}")
            if parts:
                data["comments"] = "\n\n".join(parts)

        return data

    def _process_ticket(self, ticket_data: dict[str, Any], stats: dict) -> None:
        ticket_id = ticket_data.get("ticket_id")
        if not ticket_id:
            self.logger.warning("Skipping ticket with missing identifier", extra={"metadata": ticket_data})
            stats["tickets_skipped"] += 1
            return

        self.logger.info(f"Processing ticket", extra={"metadata": {"ticket_id": ticket_id}})

        knowledge = self.extractor.extract(ticket_data)
        knowledge_dict = knowledge.model_dump() if hasattr(knowledge, "model_dump") else knowledge.__dict__

        # Fallback to direct DB fields if LLM extraction returned null for resolution/root cause
        if not knowledge_dict.get("resolution"):
            db_res = ticket_data.get("Resolution_Steps") or ticket_data.get("Close_Notes")
            if db_res:
                knowledge_dict["resolution"] = str(db_res)
        if not knowledge_dict.get("root_cause"):
            db_rca = ticket_data.get("RCA")
            if db_rca:
                knowledge_dict["root_cause"] = str(db_rca)

        if not knowledge_dict.get("resolution") and not knowledge_dict.get("root_cause"):
            self.logger.warning(f"Skipping ticket: no resolution or root cause", extra={"metadata": {"ticket_id": ticket_id}})
            stats["tickets_skipped"] += 1
            return

        self.vector_store.delete_by_ticket(ticket_id)

        chunks = self.chunker.chunk_ticket(ticket_data, knowledge_dict)
        if not chunks:
            self.logger.warning(f"No chunks created for ticket", extra={"metadata": {"ticket_id": ticket_id}})
            stats["tickets_skipped"] += 1
            return

        texts = [chunk.text for chunk in chunks]
        vectors = []

        for i in range(0, len(texts), self.embedding_batch_size):
            batch = texts[i:i + self.embedding_batch_size]
            batch_vectors = self.embedding_model.embed_batch(batch)
            vectors.extend(batch_vectors)

        payloads = []
        ids = []
        for chunk, vector in zip(chunks, vectors):
            payload = {
                **chunk.metadata,
                "ticket_id": ticket_id,
                "comment_id": ticket_data.get("comment_id"),
                "ticket_state": ticket_data.get("ticket_state"),
                "ticket_type": ticket_data.get("ticket_type"),
                "problem": knowledge_dict.get("problem"),
                "root_cause": knowledge_dict.get("root_cause"),
                "resolution": knowledge_dict.get("resolution"),
                "next_steps": knowledge_dict.get("next_steps", []),
                "text": chunk.text,
                "created_at": str(ticket_data.get("created_at", "")),
                "resolved_at": str(ticket_data.get("resolved_at", "")),
                "category": ticket_data.get("category"),
                "subcategory": ticket_data.get("subcategory"),
                "assignment_group": ticket_data.get("assignment_group"),
                "embedding_model": get_settings().embedding_model,
                "knowledge_version": get_settings().ingestion_knowledge_version,
            }
            payloads.append(payload)
            ids.append(chunk.chunk_id)

        self.vector_store.upsert(vectors, payloads, ids)

        stats["tickets_processed"] += 1
        stats["chunks_created"] += len(chunks)
        stats["vectors_upserted"] += len(vectors)

        ingestion_tickets_processed.inc()
        ingestion_chunks_created.inc(len(chunks))
        ingestion_embeddings_created.inc(len(vectors))
        ingestion_qdrant_upserts.inc(len(vectors))  # increment by number of vectors, not 1-per-ticket

    def _load_incremental(self, view_name: str, batch_size: int, since: str):
        from ingestion.mysql_loader import load_view_incremental
        return load_view_incremental(view_name, batch_size, since)

    def _load_checkpoint(self) -> str | None:
        if self.checkpoint_file.exists():
            with self.checkpoint_file.open("r") as f:
                data = json.load(f)
                return data.get("last_processed_updated_at")
        return None

    def _save_checkpoint(self, updated_at: str) -> None:
        with self.checkpoint_file.open("w") as f:
            json.dump({"last_processed_updated_at": updated_at}, f)

    def _log_failure(self, ticket_data: dict, error: Exception) -> None:
        failure = {
            "ticket_id": ticket_data.get("ticket_id"),
            "error": str(error),
            "ticket_data": {k: str(v) for k, v in ticket_data.items()},
        }
        with self.failure_log.open("a") as f:
            f.write(json.dumps(failure) + "\n")


def run_ingestion(incremental: bool = True) -> dict:
    """
    Run the ingestion process.

    Args:
        incremental: If True, only process tickets updated since last checkpoint

    Returns:
        Statistics dictionary
    """
    pipeline = IngestionPipeline()
    return pipeline.run(incremental=incremental)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run ServiceNow ticket ingestion")
    parser.add_argument("--full", action="store_true", help="Run full ingestion (ignore checkpoint)")
    parser.add_argument("--reset-checkpoint", action="store_true", help="Delete checkpoint file before running")
    args = parser.parse_args()

    if args.reset_checkpoint:
        checkpoint_file = Path(get_settings().ingestion_checkpoint_file)
        if checkpoint_file.exists():
            checkpoint_file.unlink()
            print("[+] Checkpoint reset")

    stats = run_ingestion(incremental=not args.full)
    print(f"[+] Final stats: {stats}")