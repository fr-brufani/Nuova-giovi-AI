import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import get_api_router
from .config.settings import get_settings
from .dependencies.firebase import get_firestore_client

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        # Warm up Firebase / Firestore connection at startup for faster first request.
        get_firestore_client()
        yield

    app = FastAPI(
        title="Email Agent Service",
        version="0.1.0",
        description="Service responsible for Gmail ingestion and AI concierge workflows.",
        lifespan=lifespan,
    )

    # CORS middleware - permette chiamate dal frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8080", "http://localhost:3000", "http://127.0.0.1:8080", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(get_api_router())

    @app.get("/", tags=["health"])
    async def root() -> dict[str, str]:
        return {"message": f"email-agent-service running ({settings.environment})"}

    return app

