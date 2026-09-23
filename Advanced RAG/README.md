# Advanced RAG

Agentic ticket resolution with a retrieval-augmented knowledge base built from solved ServiceNow-style issues.

## Overview

This project turns historical, solved support tickets into a searchable evidence store that can help answer new incidents using grounded retrieval and LLM-based reasoning.

At a high level, the system:

- loads solved ticket data from MySQL
- extracts structured knowledge from ticket text with an LLM
- chunks and embeds ticket content for semantic search
- stores vectors in Qdrant
- retrieves the most relevant historical tickets for a new query
- reranks evidence and generates a grounded resolution
- exposes the resolver through a FastAPI endpoint

This is not a generic chatbot. It is designed around ticket resolution workflows, where the answer must be supported by historical evidence and relevant ticket IDs.

## Key capabilities

- Incremental ingestion of updated tickets
- Structured extraction of problem, root cause, resolution, and next steps
- Ticket-aware chunking that preserves ticket context
- Dense vector search with Qdrant
- Hybrid retrieval with sparse and dense signals
- Reranking of retrieved evidence
- Confidence-based generation and fallback
- REST API for ticket resolution queries
- Metrics and logging for ingestion and resolution flow

## Architecture at a glance

```text
ServiceNow / MySQL View
        │
        ▼
Ticket Loader
        │
        ▼
LLM Knowledge Extraction
        │
        ▼
Ticket-Aware Chunking
        │
        ▼
Embeddings + Qdrant Index
        │
        ▼
Hybrid Retrieval + Rerank
        │
        ▼
Resolver Agent
        │
        ▼
Grounded Solution + Relevant Ticket IDs
```

## Repository structure

- `api/` — FastAPI routes and request/response schemas
- `config/` — settings, logging, metrics, and LLM configuration
- `embeddings/` — embedding model factory and provider integrations
- `ingestion/` — MySQL ticket loading, cleaning, and chunking pipeline
- `retrieval/` — dense, sparse, hybrid, and reranking logic
- `resolver/` — LangGraph-based resolver workflow and state
- `vectorstore/` — Qdrant integration
- `scripts/` — operational utilities for data access and evaluation
- `evaluation/` — retriever and response evaluation utilities
- `main.py` — FastAPI app bootstrap
- `requirements.txt` — Python dependencies

## Tech stack

- Python 3.10+
- FastAPI
- LangChain / LangGraph
- Qdrant
- MySQL / SQLAlchemy / PyMySQL
- pandas
- SentenceTransformers / BGE embeddings
- Prometheus metrics
- dotenv / PyYAML

## Configuration

Project configuration is centered in `config/settings.yaml` and environment variables override the defaults.

Common settings include:

- MySQL host, database, view name, batch size
- Qdrant host, port, collection name, vector size
- embedding provider/model
- LLM provider/model/base URL/API key
- retrieval top-k settings and reranker settings

Typical environment variables used by the app:

```bash
MYSQL_PASSWORD=...
API_KEY=...
```

If you want to customize the defaults, edit `config/settings.yaml` before running the project.

## Environment setup

1. Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure `.env` or the YAML settings for your environment.

Example `.env`:

```bash
MYSQL_PASSWORD=your_mysql_password
API_KEY=your_llm_api_key
```

## Running ingestion

The ingestion pipeline reads ticket records and builds the vector knowledge base.

```bash
python ingestion/ingestion.py
```

This loads solved tickets, extracts structured knowledge, generates embeddings, and upserts the results into Qdrant.

## Running the API

Start the FastAPI app:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The app exposes:

- `POST /api/v1/resolve`
- `POST /api/v1/resolve/stream`
- `GET /health` and metrics at `/metrics`

Example request:

```bash
curl -X POST "http://localhost:8000/api/v1/resolve" \
  -H "Content-Type: application/json" \
  -d '{
    "problem": "Azure DevOps migration is failing because the custom field cannot be found."
  }'
```

## Expected behavior

The resolver tries to:

1. understand the user problem
2. retrieve the most relevant historical tickets
3. rerank those candidates using stronger evidence signals
4. build a grounded evidence summary
5. generate a resolution with relevant ticket IDs and next steps
6. return a low-confidence or no-solution result when the evidence is insufficient

This means the system is intentionally conservative: it prefers evidence-backed answers over guesses.

## Operational notes

- Incremental ingestion is enabled by default for efficient reprocessing.
- Checkpoint and failure logging are managed in config values such as `.ingestion_checkpoint` and `.ingestion_failures.jsonl`.
- The system is designed to be used with a real MySQL source and an embedding/LLM backend that supports reproducible retrieval and generation.

## Practical use case

The project is well suited for support-heavy environments where:

- historical solved tickets contain valuable fixes
- ticket resolution should be evidence-based
- support agents need relevant prior incidents and proven next steps
- knowledge should be reusable beyond single-ticket search

## Notes

This repository is a practical starter implementation of an agentic advanced RAG pipeline. It focuses on real workflow integration, retrieval quality, and grounded answer generation rather than a toy demo-only app.

## Next steps

Possible extensions include:

- deeper evaluation and benchmarking of retrieval quality
- online feedback loops for user-accepted resolutions
- improved reranking policy and hybrid retrieval tuning
- ServiceNow-native integration for automated ticket recommendation
- analytics dashboards for resolution confidence and solution quality
