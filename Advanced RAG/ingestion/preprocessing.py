import json
from pathlib import Path
from typing import Any
import yaml

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from config.settings import get_settings


class TicketKnowledge(BaseModel):
    problem: str | None = Field(default=None, description="Core issue/problem statement (1-3 sentences)")
    symptoms: list[str] = Field(default_factory=list, description="Observable symptoms, error messages, failure behaviors")
    investigation: list[str] = Field(default_factory=list, description="Investigation steps, debugging actions, findings")
    root_cause: str | None = Field(default=None, description="Identified root cause")
    resolution: str | None = Field(default=None, description="Actual resolution/fix applied")
    next_steps: list[str] = Field(default_factory=list, description="Recommended follow-up actions, verification steps, preventive measures")
    technical_entities: list[str] = Field(default_factory=list, description="Technical entities: product names, field names, error codes, config keys, tool names, versions")


class TicketKnowledgeExtractor:
    """
    Extracts structured technical knowledge from solved ServiceNow tickets.

    The prompt is loaded once during initialization, and the
    LangChain chain is reused for every extraction request.
    """

    def __init__(self, llm):
        self.llm = llm
        self.parser = JsonOutputParser(pydantic_object=TicketKnowledge)
        self.prompt = self._load_prompt()
        self.chain = self.prompt | self.llm | self.parser

    def _load_prompt(self) -> ChatPromptTemplate:
        """Load the extraction prompt from the YAML file."""
        settings = get_settings()
        project_root = Path(__file__).resolve().parents[1]
        prompt_path = project_root / "prompts" / "TicketCleaningPrompt.yaml"

        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Prompt file not found at {prompt_path}."
            )

        with prompt_path.open("r", encoding="utf-8") as f:
            cleaning_prompt = yaml.safe_load(f)

        return ChatPromptTemplate.from_messages(
            [
                ("system", cleaning_prompt["system"]),
                ("human", cleaning_prompt["human"]),
            ]
        ).partial(format_instructions=self.parser.get_format_instructions())

    def extract(self, ticket_data: dict[str, Any]) -> TicketKnowledge:
        """
        Extract structured knowledge from a ticket.

        Args:
            ticket_data: Dictionary with ticket fields including comments

        Returns:
            TicketKnowledge object with extracted structured information
        """
        comments = ticket_data.get("comments", "")
        if not comments or not comments.strip():
            return TicketKnowledge()

        try:
            result = self.chain.invoke({
                "ticket_id": ticket_data.get("ticket_id", ""),
                "ticket_state": ticket_data.get("ticket_state", ""),
                "ticket_type": ticket_data.get("ticket_type", ""),
                "priority": ticket_data.get("priority", ""),
                "category": ticket_data.get("category", ""),
                "subcategory": ticket_data.get("subcategory", ""),
                "assignment_group": ticket_data.get("assignment_group", ""),
                "resolution_code": ticket_data.get("resolution_code", ""),
                "created_at": ticket_data.get("created_at", ""),
                "resolved_at": ticket_data.get("resolved_at", ""),
                "comments": comments,
            })
            return TicketKnowledge(**result)
        except Exception:
            return TicketKnowledge()


class TicketCleaner:
    """
    Backward-compatible simple cleaner that uses the knowledge extractor
    and returns a cleaned text representation.
    """

    def __init__(self, llm):
        self.extractor = TicketKnowledgeExtractor(llm)

    def clean(self, comment_text: str) -> str:
        """
        Clean a single ServiceNow comment (backward compatible).

        Args:
            comment_text: Raw comment text.

        Returns:
            Cleaned comment text.
        """
        if not comment_text or not comment_text.strip():
            return ""

        ticket_data = {"comments": comment_text, "ticket_id": "unknown"}
        knowledge = self.extractor.extract(ticket_data)

        parts = []
        if knowledge.problem:
            parts.append(f"Problem: {knowledge.problem}")
        if knowledge.symptoms:
            parts.append(f"Symptoms: {'; '.join(knowledge.symptoms)}")
        if knowledge.investigation:
            parts.append(f"Investigation: {'; '.join(knowledge.investigation)}")
        if knowledge.root_cause:
            parts.append(f"Root Cause: {knowledge.root_cause}")
        if knowledge.resolution:
            parts.append(f"Resolution: {knowledge.resolution}")
        if knowledge.next_steps:
            parts.append(f"Next Steps: {'; '.join(knowledge.next_steps)}")
        if knowledge.technical_entities:
            parts.append(f"Entities: {', '.join(knowledge.technical_entities)}")

        return "\n\n".join(parts)
