import os
import uvicorn

from email_agent_service import create_app

app = create_app()

# Cloud Run imposta PORT automaticamente, altrimenti usa 8000 per locale
PORT = int(os.environ.get("PORT", 8000))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        reload=True,
    )

