from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from email_agent_service.config.settings import get_settings
from email_agent_service.app import create_app


def test_health_endpoints(monkeypatch) -> None:
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "https://example.com/callback")
    get_settings.cache_clear()

    monkeypatch.setattr("email_agent_service.app.get_firestore_client", lambda: None)

    app = create_app()
    with TestClient(app) as client:
        live_response = client.get("/health/live")
        ready_response = client.get("/health/ready")
        root_response = client.get("/")

    assert live_response.status_code == 200
    assert live_response.json() == {"status": "ok"}
    assert ready_response.status_code == 200
    assert ready_response.json() == {"status": "ready"}
    assert root_response.status_code == 200
    assert root_response.json()["message"].startswith("email-agent-service running")

    get_settings.cache_clear()

