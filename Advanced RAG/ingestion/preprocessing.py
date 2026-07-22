from pathlib import Path

import yaml
from langchain_core.prompts import ChatPromptTemplate


class TicketCleaner:
    """
    Cleans ServiceNow ticket comments using an LLM.

    The prompt is loaded only once during initialization, and the
    LangChain chain is reused for every cleaning request.
    """

    def __init__(self, llm):
        self.llm = llm
        self.prompt = self._load_prompt()
        self.chain = self.prompt | self.llm

    @staticmethod
    def _load_prompt() -> ChatPromptTemplate:
        """Load the cleaning prompt from the YAML file."""

        project_root = Path(__file__).resolve().parents[2]
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
        )

    def clean(self, comment_text: str) -> str:
        """
        Clean a single ServiceNow comment.

        Args:
            comment_text: Raw comment text.

        Returns:
            Cleaned comment text.
        """
        if not comment_text or not comment_text.strip():
            return ""

        response = self.chain.invoke({"input": comment_text})
        return response.content.strip()