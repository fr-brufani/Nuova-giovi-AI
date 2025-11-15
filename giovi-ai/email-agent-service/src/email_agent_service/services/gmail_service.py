from __future__ import annotations

import base64
from datetime import timezone
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build

from ..config.settings import get_settings
from ..repositories import HostEmailIntegrationRepository
from ..repositories.host_email_integrations import HostEmailIntegrationRecord
from ..utils.crypto import decrypt_optional_text, decrypt_text


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

    def _gmail(self, integration: HostEmailIntegrationRecord) -> Resource:
        credentials = self._build_credentials(integration)
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
        gmail = self._gmail(integration)
        request = (
            gmail.users()
            .messages()
            .list(userId="me", q=query, pageToken=page_token, maxResults=max_results)
        )
        return request.execute()

    def get_message_raw(self, integration: HostEmailIntegrationRecord, message_id: str) -> dict:
        gmail = self._gmail(integration)
        return (
            gmail.users()
            .messages()
            .get(userId="me", id=message_id, format="raw", metadataHeaders=["Subject"])
            .execute()
        )

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

