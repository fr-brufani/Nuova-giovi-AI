from __future__ import annotations

import base64
import logging
import time
from datetime import timezone
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

from ..config.settings import get_settings
from ..repositories import HostEmailIntegrationRepository
from ..repositories.host_email_integrations import HostEmailIntegrationRecord
from ..utils.crypto import decrypt_optional_text, decrypt_text

logger = logging.getLogger(__name__)


class GmailService:
    def __init__(self, integration_repo: HostEmailIntegrationRepository):
        self._settings = get_settings()
        self._integration_repo = integration_repo

    def _build_credentials(self, integration: HostEmailIntegrationRecord) -> Credentials:
        access_token = decrypt_text(integration.encrypted_access_token)
        refresh_token = decrypt_optional_text(integration.encrypted_refresh_token)
        
        # NON impostiamo expiry inizialmente - causava problemi con datetime timezone-aware vs naive
        # Google OAuth gestirà automaticamente l'expiry e faremo il refresh se necessario
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self._settings.google_oauth_client_id,
            client_secret=self._settings.google_oauth_client_secret,
            scopes=integration.scopes or self._settings.google_oauth_scopes,
        )

        # Non impostiamo expiry qui - lasceremo che Google lo gestisca durante il refresh automatico
        # Questo evita problemi con datetime timezone-naive vs timezone-aware
        
        return credentials

    def _refresh_credentials_if_needed(self, integration: HostEmailIntegrationRecord, credentials: Credentials) -> None:
        """Refresh delle credenziali se necessario, con retry e timeout più lunghi."""
        if credentials.valid:
            return
        
        if not credentials.refresh_token:
            raise ValueError("Refresh token non disponibile. È necessario riconnettere l'integrazione Gmail.")
        
        logger.info("[GMAIL_SERVICE] Token scaduto, tentativo refresh...")
        
        # Crea un Request object con timeout più lungo
        request = Request()
        max_retries = 3
        retry_delay = 2  # secondi
        
        for attempt in range(max_retries):
            try:
                credentials.refresh(request)
                logger.info(f"[GMAIL_SERVICE] ✅ Token refresh riuscito (tentativo {attempt + 1})")
                
                # Salva il nuovo token in Firestore
                if credentials.token:
                    from ..utils.crypto import encrypt_text
                    encrypted_token = encrypt_text(credentials.token)
                    self._integration_repo.update_access_token(integration.email, encrypted_token)
                    logger.info("[GMAIL_SERVICE] Nuovo access token salvato in Firestore")
                
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"[GMAIL_SERVICE] ⚠️ Refresh fallito (tentativo {attempt + 1}/{max_retries}): {e}. Retry tra {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"[GMAIL_SERVICE] ❌ Refresh fallito dopo {max_retries} tentativi: {e}")
                    raise

    def _gmail(self, integration: HostEmailIntegrationRecord) -> Resource:
        credentials = self._build_credentials(integration)
        # Refresh delle credenziali se necessario prima di creare il service
        self._refresh_credentials_if_needed(integration, credentials)
        service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        return service

    def list_messages(
        self,
        integration: HostEmailIntegrationRecord,
        query: str,
        *,
        page_token: Optional[str] = None,
        max_results: int = 100,
    ) -> dict:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                gmail = self._gmail(integration)
                request = (
                    gmail.users()
                    .messages()
                    .list(userId="me", q=query, pageToken=page_token, maxResults=max_results)
                )
                return request.execute()
            except HttpError as e:
                if e.resp.status == 401 and attempt < max_retries - 1:
                    # Token scaduto, prova a refreshare e riprova
                    logger.warning(f"[GMAIL_SERVICE] 401 Unauthorized (tentativo {attempt + 1}), refresh token e retry...")
                    credentials = self._build_credentials(integration)
                    self._refresh_credentials_if_needed(integration, credentials)
                    time.sleep(1)
                    continue
                raise
            except Exception as e:
                if "timeout" in str(e).lower() and attempt < max_retries - 1:
                    logger.warning(f"[GMAIL_SERVICE] Timeout (tentativo {attempt + 1}), retry...")
                    time.sleep(2)
                    continue
                raise

    def get_message_raw(self, integration: HostEmailIntegrationRecord, message_id: str) -> dict:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                gmail = self._gmail(integration)
                return (
                    gmail.users()
                    .messages()
                    .get(userId="me", id=message_id, format="raw", metadataHeaders=["Subject"])
                    .execute()
                )
            except HttpError as e:
                if e.resp.status == 401 and attempt < max_retries - 1:
                    # Token scaduto, prova a refreshare e riprova
                    logger.warning(f"[GMAIL_SERVICE] 401 Unauthorized per message {message_id} (tentativo {attempt + 1}), refresh token e retry...")
                    credentials = self._build_credentials(integration)
                    self._refresh_credentials_if_needed(integration, credentials)
                    time.sleep(1)
                    continue
                raise
            except Exception as e:
                if "timeout" in str(e).lower() and attempt < max_retries - 1:
                    logger.warning(f"[GMAIL_SERVICE] Timeout per message {message_id} (tentativo {attempt + 1}), retry...")
                    time.sleep(2)
                    continue
                raise

    def get_integration(self, email: str) -> Optional[HostEmailIntegrationRecord]:
        return self._integration_repo.get_by_email(email)

    def setup_watch(
        self,
        integration: HostEmailIntegrationRecord,
        topic_name: str,
    ) -> dict:
        """
        Configura Gmail watch per ricevere notifiche via Pub/Sub.
        
        Args:
            integration: Record integrazione Gmail
            topic_name: Nome completo del topic Pub/Sub (es: projects/PROJECT_ID/topics/TOPIC_NAME)
        
        Returns:
            dict con historyId e expiration (millisecondi)
        """
        gmail = self._gmail(integration)
        request = gmail.users().watch(
            userId="me",
            body={
                "labelIds": ["INBOX"],
                "topicName": topic_name,
            },
        )
        response = request.execute()
        return {
            "historyId": response.get("historyId"),
            "expiration": response.get("expiration"),  # Millisecondi da epoch
        }

    def get_history(
        self,
        integration: HostEmailIntegrationRecord,
        start_history_id: str,
    ) -> dict:
        """
        Recupera history Gmail da un historyId specifico.
        
        Args:
            integration: Record integrazione Gmail
            start_history_id: History ID da cui iniziare
        
        Returns:
            dict con history records
        """
        gmail = self._gmail(integration)
        request = gmail.users().history().list(
            userId="me",
            startHistoryId=start_history_id,
            historyTypes=["messageAdded"],
        )
        return request.execute()

    def send_reply(
        self,
        integration: HostEmailIntegrationRecord,
        to_email: str,
        subject: str,
        body: str,
        reply_to: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None,
    ) -> dict:
        """
        Invia una risposta email tramite Gmail API con threading corretto.
        
        Args:
            integration: Record integrazione Gmail
            to_email: Indirizzo email destinatario
            subject: Oggetto email (verrà aggiunto "Re: " se non presente)
            body: Corpo del messaggio
            reply_to: Indirizzo Reply-To (opzionale)
            in_reply_to: Message-ID originale per threading (opzionale)
            references: References header per threading (opzionale)
        
        Returns:
            dict con messageId e threadId della risposta inviata
        """
        # Assicura che l'oggetto inizi con "Re: " se non presente
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"
        
        # Costruisci l'email in formato RFC822
        email_lines = [
            f"To: {to_email}",
            f"Subject: {subject}",
            "Content-Type: text/plain; charset=utf-8",
        ]
        
        if reply_to:
            email_lines.insert(1, f"Reply-To: {reply_to}")
        
        if in_reply_to:
            email_lines.append(f"In-Reply-To: {in_reply_to}")
        if references:
            email_lines.append(f"References: {references}")
        
        email_lines.append("")  # Riga vuota obbligatoria prima del corpo
        email_lines.append(body)
        
        email = "\r\n".join(email_lines)
        
        # Codifica l'email in base64url (richiesto da Gmail API)
        email_bytes = email.encode("utf-8")
        base64_encoded = base64.urlsafe_b64encode(email_bytes).decode("ascii")
        base64_encoded = base64_encoded.rstrip("=")  # Rimuovi padding
        
        # Invia tramite Gmail API
        gmail = self._gmail(integration)
        request = gmail.users().messages().send(
            userId="me",
            body={"raw": base64_encoded},
        )
        response = request.execute()
        
        return {
            "messageId": response.get("id"),
            "threadId": response.get("threadId"),
        }

