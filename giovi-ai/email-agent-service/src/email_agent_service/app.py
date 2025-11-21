import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import get_api_router
from .config.settings import get_settings
from .dependencies.firebase import get_firestore_client
from .services import ScidooReservationPollingService, PersistenceService

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Warm up Firebase / Firestore connection at startup for faster first request.
        firestore_client = get_firestore_client()
        
        # Avvia polling services
        persistence_service = PersistenceService(firestore_client)
        
        # Crea e avvia servizi di polling
        scidoo_polling_service = None
        
        try:
            # Avvia Scidoo polling service
            scidoo_polling_service = ScidooReservationPollingService(
                persistence_service=persistence_service,
                firestore_client=firestore_client,
            )
            scidoo_polling_service.start()
            logging.info("[APP] ScidooReservationPollingService avviato")
        except Exception as e:
            logging.error(f"[APP] Errore avvio ScidooReservationPollingService: {e}", exc_info=True)
        
        # Salva istanze nell'app state per accesso dagli endpoint
        # NOTA: Smoobu ora usa webhooks invece di polling
        app.state.scidoo_polling_service = scidoo_polling_service
        
        yield
        
        # Cleanup: ferma polling services
        # NOTA: Smoobu ora usa webhooks invece di polling
        try:
            if scidoo_polling_service:
                scidoo_polling_service.stop()
                logging.info("[APP] ScidooReservationPollingService fermato")
        except Exception as e:
            logging.error(f"[APP] Errore fermata ScidooReservationPollingService: {e}", exc_info=True)

    app = FastAPI(
        title="Email Agent Service",
        version="0.1.0",
        description="Service responsible for Gmail ingestion and AI concierge workflows.",
        lifespan=lifespan,
    )

    # CORS middleware - permette chiamate dal frontend
    # Permette tutte le origini (in produzione potrebbe essere più restrittivo)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8080",
            "http://localhost:3000",
            "http://127.0.0.1:8080",
            "http://127.0.0.1:3000",
            "https://giovi-ai.web.app",
            "https://giovi-ai.firebaseapp.com",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(get_api_router())

    @app.get("/", tags=["health"])
    async def root() -> dict[str, str]:
        return {"message": f"email-agent-service running ({settings.environment})"}

    return app

