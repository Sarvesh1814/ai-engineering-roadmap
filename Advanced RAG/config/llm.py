from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from config.settings import get_settings


def get_llm():
    settings = get_settings()

    provider = settings.llm_provider

    if provider == "ollama":
        return ChatOllama(
            model=settings.llm_model_name,
            base_url=settings.llm_base_url,
            temperature=settings.llm_temperature,
        )

    elif provider == "openai":
        return ChatOpenAI(
            model=settings.llm_model_name,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            temperature=settings.llm_temperature,
        )

    else:
        raise ValueError(f"Unsupported provider: {provider}")