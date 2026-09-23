import hashlib
import uuid
from dataclasses import dataclass
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.settings import get_settings


@dataclass
class Chunk:
    chunk_id: str
    ticket_id: str
    comment_id: str | None
    chunk_index: int
    chunk_type: str
    text: str
    metadata: dict[str, Any]


class TicketAwareChunker:
    """
    Ticket-aware chunking that preserves logical sections (problem, symptoms,
    investigation, root_cause, resolution, next_steps) and then applies
    recursive token-aware splitting for large sections.
    """

    CHUNK_TYPES = [
        "problem",
        "symptoms",
        "investigation",
        "root_cause",
        "resolution",
        "next_steps",
        "conversation",
    ]

    def __init__(self):
        settings = get_settings()
        self.chunk_size = settings.chunking_chunk_size
        self.chunk_overlap = settings.chunking_chunk_overlap
        self.min_chunk_size = settings.chunking_min_chunk_size

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def chunk_ticket(self, ticket_data: dict[str, Any], knowledge: dict[str, Any]) -> list[Chunk]:
        """
        Chunk a ticket into logical sections, then recursively split large sections.

        Args:
            ticket_data: Raw ticket data from MySQL
            knowledge: Structured knowledge from TicketKnowledgeExtractor

        Returns:
            List of Chunk objects with deterministic IDs
        """
        ticket_id = ticket_data.get("ticket_id", "unknown")
        comment_id = ticket_data.get("comment_id")

        sections = self._build_sections(knowledge)
        chunks = []

        for chunk_type, content in sections.items():
            if not content or not content.strip():
                continue

            section_chunks = self._chunk_section(
                ticket_id=ticket_id,
                comment_id=comment_id,
                chunk_type=chunk_type,
                content=content,
            )
            chunks.extend(section_chunks)

        return chunks

    def _build_sections(self, knowledge: dict[str, Any]) -> dict[str, str]:
        """Build logical sections from extracted knowledge."""
        sections = {}

        if knowledge.get("problem"):
            sections["problem"] = knowledge["problem"]

        if knowledge.get("symptoms"):
            sections["symptoms"] = "\n".join(f"- {s}" for s in knowledge["symptoms"])

        if knowledge.get("investigation"):
            sections["investigation"] = "\n".join(f"- {s}" for s in knowledge["investigation"])

        if knowledge.get("root_cause"):
            sections["root_cause"] = knowledge["root_cause"]

        if knowledge.get("resolution"):
            sections["resolution"] = knowledge["resolution"]

        if knowledge.get("next_steps"):
            sections["next_steps"] = "\n".join(f"{i+1}. {s}" for i, s in enumerate(knowledge["next_steps"]))

        if knowledge.get("technical_entities"):
            sections["conversation"] = f"Technical Entities: {', '.join(knowledge['technical_entities'])}"

        return sections

    def _chunk_section(
        self,
        ticket_id: str,
        comment_id: str | None,
        chunk_type: str,
        content: str,
    ) -> list[Chunk]:
        """Split a section into chunks if needed."""
        if len(content) <= self.chunk_size:
            return [self._create_chunk(
                ticket_id=ticket_id,
                comment_id=comment_id,
                chunk_type=chunk_type,
                chunk_index=0,
                text=content,
            )]

        splits = self.splitter.split_text(content)
        chunks = []
        for i, split in enumerate(splits):
            if len(split) < self.min_chunk_size and i > 0:
                chunks[-1] = Chunk(
                    chunk_id=chunks[-1].chunk_id,
                    ticket_id=chunks[-1].ticket_id,
                    comment_id=chunks[-1].comment_id,
                    chunk_index=chunks[-1].chunk_index,
                    chunk_type=chunks[-1].chunk_type,
                    text=chunks[-1].text + "\n" + split,
                    metadata=chunks[-1].metadata,
                )
            else:
                chunks.append(self._create_chunk(
                    ticket_id=ticket_id,
                    comment_id=comment_id,
                    chunk_type=chunk_type,
                    chunk_index=i,
                    text=split,
                ))

        return chunks

    def _create_chunk(
        self,
        ticket_id: str,
        comment_id: str | None,
        chunk_type: str,
        chunk_index: int,
        text: str,
    ) -> Chunk:
        """Create a chunk with deterministic ID."""
        content_hash = hashlib.sha256(text.encode()).hexdigest()[:12]
        raw_hash = hashlib.sha256(
            f"{ticket_id}:{content_hash}:{chunk_index}".encode()
        ).hexdigest()
        # Qdrant requires point IDs to be unsigned integers or UUIDs.
        # Take the first 32 hex chars of the SHA-256 digest and format as UUID.
        chunk_id = str(uuid.UUID(hex=raw_hash[:32]))

        metadata = {
            "ticket_id": ticket_id,
            "comment_id": comment_id,
            "chunk_index": chunk_index,
            "chunk_type": chunk_type,
            "content_hash": content_hash,
        }

        return Chunk(
            chunk_id=chunk_id,
            ticket_id=ticket_id,
            comment_id=comment_id,
            chunk_index=chunk_index,
            chunk_type=chunk_type,
            text=text,
            metadata=metadata,
        )


def chunk_text(text: str, chunk_size: int | None = None, chunk_overlap: int | None = None) -> list[str]:
    """Simple fallback chunker for raw text."""
    settings = get_settings()
    size = chunk_size or settings.chunking_chunk_size
    overlap = chunk_overlap or settings.chunking_chunk_overlap

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        length_function=len,
    )
    return splitter.split_text(text)