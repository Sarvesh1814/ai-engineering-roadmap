import yaml
import os
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from dotenv  import load_dotenv

# Load environment variables from a .env file
load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER")
MODEL_NAME = os.getenv("MODEL_NAME")
BASE_URL = os.getenv("BASE_URL")
API_KEY = os.getenv("API_KEY")
TEMPERATURE = float(os.getenv("CTEMPERATURE", 0.1))  # Default to 0.1 if not set
def get_llm():

    provider = LLM_PROVIDER

    if provider == "ollama":

        return ChatOllama(
            model=MODEL_NAME,
            base_url=BASE_URL,
            temperature=TEMPERATURE,
        )

    elif provider == "openai":

        return ChatOpenAI(
            model=MODEL_NAME,
            base_url=BASE_URL,
            api_key=API_KEY,
            temperature=TEMPERATURE
        )

    else:
        raise ValueError(f"Unsupported provider: {provider}")