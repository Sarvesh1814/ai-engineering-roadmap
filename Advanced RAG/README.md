# Advanced RAG Pipeline

A practical Retrieval-Augmented Generation (RAG) project designed to ingest, clean, and prepare ticket-like data for downstream vector search and semantic retrieval.

## Overview

This project demonstrates an end-to-end RAG workflow using:

- Python for orchestration
- LangChain for LLM prompt chaining
- Ollama or OpenAI for text cleaning and reasoning
- Qdrant for vector storage and similarity search
- MySQL and SQLAlchemy for data ingestion

The main goal is to take raw support or service data, clean it with an LLM, and make it ready for retrieval-based applications.

## What the project does

1. Loads data from a MySQL view
2. Passes ticket comments through an LLM-based cleaning pipeline
3. Configures the LLM provider using environment variables
4. Prepares the data for embedding and vector storage
5. Supports integration with a Qdrant vector database

## Project structure

- config/ - LLM configuration and environment-based setup
- embeddings/ - embedding model abstractions and factory logic
- ingestion/ - data loading and preprocessing pipelines
- prompts/ - prompt templates used for ticket cleaning
- vectorstore/ - Qdrant connection and collection management
- requirements.txt - Python dependencies

## Tech stack

- Python
- LangChain
- LangGraph
- SQLAlchemy
- pandas
- PyYAML
- Qdrant Client
- Sentence Transformers
- PyMySQL
- dotenv

## Setup

1. Create and activate a Python environment
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables in a .env file for:
   - LLM provider
   - model name
   - base URL
   - API key (if needed)
   - MySQL connection details

4. Run the ingestion flow:

```bash
python ingestion/ingestion.py
```

## Notes

This repository is a learning-oriented implementation of an Advanced RAG workflow. It focuses on building the core pipeline rather than offering a fully production-ready product.

## Future direction

Possible extensions include:

- embedding generation and indexing
- semantic search over cleaned ticket data
- evaluation of retrieval quality
- integration with a full RAG chat application
