from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

REGISTRY = CollectorRegistry()

ingestion_tickets_processed = Counter(
    "ingestion_tickets_processed_total",
    "Total number of tickets processed",
    registry=REGISTRY,
)

ingestion_tickets_failed = Counter(
    "ingestion_tickets_failed_total",
    "Total number of tickets that failed processing",
    registry=REGISTRY,
)

ingestion_chunks_created = Counter(
    "ingestion_chunks_created_total",
    "Total number of chunks created",
    registry=REGISTRY,
)

ingestion_embeddings_created = Counter(
    "ingestion_embeddings_created_total",
    "Total number of embeddings created",
    registry=REGISTRY,
)

ingestion_qdrant_upserts = Counter(
    "ingestion_qdrant_upserts_total",
    "Total number of Qdrant upsert operations",
    registry=REGISTRY,
)

ingestion_latency = Histogram(
    "ingestion_latency_seconds",
    "Ingestion pipeline latency in seconds",
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
    registry=REGISTRY,
)

queries_total = Counter(
    "queries_total",
    "Total number of queries processed",
    registry=REGISTRY,
)

retrieval_latency = Histogram(
    "retrieval_latency_seconds",
    "Dense retrieval latency in seconds",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0],
    registry=REGISTRY,
)

reranking_latency = Histogram(
    "reranking_latency_seconds",
    "Reranking latency in seconds",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0],
    registry=REGISTRY,
)

generation_latency = Histogram(
    "generation_latency_seconds",
    "LLM generation latency in seconds",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
    registry=REGISTRY,
)

end_to_end_latency = Histogram(
    "end_to_end_latency_seconds",
    "End-to-end query latency in seconds",
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
    registry=REGISTRY,
)

no_solution_rate = Counter(
    "no_solution_total",
    "Total number of queries with no reliable solution",
    registry=REGISTRY,
)

low_confidence_rate = Counter(
    "low_confidence_total",
    "Total number of queries with low confidence",
    registry=REGISTRY,
)

average_retrieved_tickets = Gauge(
    "average_retrieved_tickets",
    "Average number of tickets retrieved per query",
    registry=REGISTRY,
)

active_requests = Gauge(
    "active_requests",
    "Number of currently active requests",
    registry=REGISTRY,
)