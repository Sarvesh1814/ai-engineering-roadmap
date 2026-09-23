from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from api.routes import resolver, health
from config import get_settings, get_logger
from config.logging import setup_logging
from config.metrics import REGISTRY


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger = get_logger("main")
    logger.info("Application starting up")

    # Initialize the ResolverAgent (heavy: loads LLM, connects Qdrant, builds BM25
    # index, loads CrossEncoder) in the lifespan so it is ready before the first
    # request arrives, and so blocking I/O doesn't freeze the event loop mid-request.
    from resolver.graph import ResolverAgent
    logger.info("Initializing resolver agent (this may take a moment)...")
    app.state.resolver_agent = await asyncio.to_thread(ResolverAgent)
    logger.info("Resolver agent ready")

    yield

    logger.info("Application shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Advanced RAG - Agentic Ticket Resolver",
        description="ServiceNow ticket resolution using agentic RAG with hybrid search and reranking",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(resolver.router)
    app.include_router(health.router)

    metrics_app = make_asgi_app(registry=REGISTRY)
    app.mount("/metrics", metrics_app)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )