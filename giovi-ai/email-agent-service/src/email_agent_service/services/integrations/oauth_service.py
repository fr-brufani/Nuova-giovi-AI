from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

import requests
from google.auth.exceptions import GoogleAuthError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from ...config.settings import get_settings
from ...repositories import HostEmailIntegrationRepository, OAuthStateRepository
from ...repositories.host_email_integrations import HostEmailIntegrationRecord
from ...repositories.oauth_states import OAuthStateRecord
from ...utils.crypto import encrypt_text


class OAuthStateNotFoundError(Exception):
    pass


class OAuthStateExpiredError(Exception):
    pass


class OAuthTokenExchangeError(Exception):
    pass


class GmailOAuthService:
    def __init__(
        self,
        oauth_state_repository: OAuthStateRepository,
        integration_repository: HostEmailIntegrationRepository,
        *,
        state_ttl_minutes: int = 10,
    ) -> None:
        self._settings = get_settings()
        self._oauth_state_repository = oauth_state_repository
        self._integration_repository = integration_repository
        self._state_ttl = timedelta(minutes=state_ttl_minutes)

    def _build_flow(self, redirect_uri: Optional[str]) -> Flow:
        config = {
            "web": {
                "client_id": self._settings.google_oauth_client_id,
                "client_secret": self._settings.google_oauth_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
        redirect = redirect_uri or self._settings.google_oauth_redirect_uri
        flow = Flow.from_client_config(config, scopes=self._settings.google_oauth_scopes)
        if redirect:
            flow.redirect_uri = redirect
        return flow

    def generate_authorization_url(
        self,
        *,
        host_id: str,
        email: str,
        pms_provider: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ) -> tuple[str, str, datetime]:
        flow = self._build_flow(redirect_uri)
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )

        expires_at = datetime.now(timezone.utc) + self._state_ttl
        record = OAuthStateRecord(state=state, host_uid=host_id, expires_at=expires_at)
        self._oauth_state_repository.create_state(record)

        return authorization_url, state, expires_at

    def _validate_state(self, state: str) -> OAuthStateRecord:
        record = self._oauth_state_repository.get_state(state)
        if record is None:
            raise OAuthStateNotFoundError("OAuth state not found or already used")

        now = datetime.now(timezone.utc)
        if record.expires_at and record.expires_at < now:
            raise OAuthStateExpiredError("OAuth state has expired")
        return record

    def _encrypt_token(self, token: Optional[str]) -> Optional[str]:
        if not token:
            return None
        return encrypt_text(token)

    def _store_integration(
        self,
        *,
        email: str,
        host_id: str,
        provider: str,
        credentials: Credentials,
        scopes: Sequence[str],
        pms_provider: Optional[str] = None,
    ) -> HostEmailIntegrationRecord:
        encrypted_access = self._encrypt_token(credentials.token)
        encrypted_refresh = self._encrypt_token(credentials.refresh_token)
        record = HostEmailIntegrationRecord(
            email=email,
            host_id=host_id,
            provider=provider,
            encrypted_access_token=encrypted_access or "",
            encrypted_refresh_token=encrypted_refresh,
            scopes=scopes,
            token_expiry=credentials.expiry,
            pms_provider=pms_provider,
        )
        self._integration_repository.upsert_integration(record)
        return record

    def handle_callback(
        self,
        *,
        state: str,
        code: str,
        email: str,
        pms_provider: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ) -> HostEmailIntegrationRecord:
        state_record = self._validate_state(state)

        flow = self._build_flow(redirect_uri)

        # Google può aggiungere scope extra (openid, userinfo, ecc.) automaticamente
        # oauthlib solleva un'eccezione "Scope has changed" quando gli scope restituiti sono diversi
        # Soluzione: imposta OAUTHLIB_RELAX_TOKEN_SCOPE per permettere scope extra
        import os
        
        # Configura oauthlib per non sollevare eccezioni quando Google aggiunge scope extra
        # Questa è la soluzione corretta invece di cercare di intercettare eccezioni
        original_env = os.environ.get('OAUTHLIB_RELAX_TOKEN_SCOPE')
        try:
            os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
            
            # Ora fetch_token non solleverà eccezioni per scope changes
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
        except GoogleAuthError as exc:
            error_msg = str(exc)
            # "invalid_grant" può significare code già usato o scaduto
            if "invalid_grant" in error_msg.lower():
                raise OAuthTokenExchangeError("Authorization code already used or expired. Please try connecting again.") from exc
            raise OAuthTokenExchangeError(f"Failed to exchange authorization code: {error_msg}") from exc
        finally:
            # Ripristina la variabile d'ambiente originale
            if original_env is None:
                os.environ.pop('OAUTHLIB_RELAX_TOKEN_SCOPE', None)
            else:
                os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = original_env

        # Verifica che le credenziali siano disponibili
        if credentials is None:
            raise OAuthTokenExchangeError("Failed to obtain OAuth credentials after token exchange")
        
        scopes = credentials.scopes or self._settings.google_oauth_scopes

        integration_record = self._store_integration(
            email=email,
            host_id=state_record.host_uid,
            provider="gmail",
            credentials=credentials,
            scopes=scopes,
            pms_provider=pms_provider,
        )

        self._oauth_state_repository.delete_state(state)

        return integration_record

