from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agency_service.config import settings
from agency_service.routes import router as api_router

app = FastAPI(
    title="Giovi AI - Agency Service",
    version="0.1.0",
    description="API dedicate alle agenzie di pulizie",
)

allowed_origins = settings.allowed_origins or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok", "service": "agency-service"}


app.include_router(api_router, prefix="/api")

