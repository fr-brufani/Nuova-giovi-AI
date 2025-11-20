"""Client per Booking.com Messaging API."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional
from unittest.mock import Mock

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ...config.settings import get_settings
from ...models.booking_message import BookingMessage

logger = logging.getLogger(__name__)


class BookingAPIError(Exception):
    """Eccezione base per errori API Booking.com."""

    pass


class BookingAuthenticationError(BookingAPIError):
    """Errore di autenticazione (401)."""

    pass


class BookingForbiddenError(BookingAPIError):
    """Accesso negato (403)."""

    pass


class BookingRateLimitError(BookingAPIError):
    """Rate limit superato (429)."""

    pass


class BookingMessagingClient:
    """Client per Booking.com Messaging API con supporto mock mode."""

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        base_url: Optional[str] = None,
        api_version: Optional[str] = None,
        mock_mode: Optional[bool] = None,
    ) -> None:
        """
        Inizializza client Messaging API.
        
        Args:
            username: Username Machine Account (opzionale se mock_mode=True)
            password: Password Machine Account (opzionale se mock_mode=True)
            base_url: Base URL API (default da settings)
            api_version: Versione API (default "1.2")
            mock_mode: Se True, usa mock responses invece di chiamate reali
        """
        self._settings = get_settings()
        self.username = username or self._settings.booking_api_username
        self.password = password or self._settings.booking_api_password
        self.base_url = base_url or self._settings.booking_messaging_api_base_url
        self.api_version = api_version or self._settings.booking_api_version
        
        # Mock mode se non ci sono credenziali o esplicitamente richiesto
        self.mock_mode = (
            mock_mode
            if mock_mode is not None
            else not (self.username and self.password)
        )
        
        if self.mock_mode:
            logger.info("[BookingMessagingClient] Initialized in MOCK MODE - using mock responses")
            self._init_mock_responses()
        else:
            logger.info(f"[BookingMessagingClient] Initialized in PRODUCTION MODE - API: {self.base_url}")
            self._init_session()
    
    def _init_session(self) -> None:
        """Inizializza session HTTP con retry logic."""
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
    
    def _init_mock_responses(self) -> None:
        """Inizializza mock responses per sviluppo senza credenziali."""
        self._mock_responses = {
            "messages_latest": {
                "meta": {"ruid": "mock-ruid-123"},
                "warnings": [],
                "data": {
                    "messages": [
                        {
                            "message_id": "mock-msg-001",
                            "message_type": "free_text",
                            "content": "Test message from guest",
                            "timestamp": "2025-01-15T10:00:00Z",
                            "sender": {
                                "participant_id": "mock-guest-123",
                                "metadata": {
                                    "participant_type": "GUEST",
                                    "name": "Test Guest",
                                },
                            },
                            "conversation": {
                                "conversation_id": "mock-conv-123",
                                "conversation_type": "reservation",
                                "conversation_reference": "9876543210",
                            },
                            "attachment_ids": [],
                        }
                    ],
                    "ok": True,
                    "number_of_messages": 1,
                    "timestamp": "2025-01-15T10:00:00Z",
                },
                "errors": [],
            },
            "conversation_by_reservation": {
                "meta": {"ruid": "mock-ruid-456"},
                "warnings": [],
                "data": {
                    "ok": "true",
                    "conversation": {
                        "conversation_id": "mock-conv-123",
                        "conversation_type": "reservation",
                        "conversation_reference": "9876543210",
                        "access": "read_write",
                        "participants": [
                            {
                                "participant_id": "mock-guest-123",
                                "metadata": {"type": "guest", "name": "Test Guest"},
                            },
                            {
                                "participant_id": "mock-property-456",
                                "metadata": {"type": "property", "id": "8011855"},
                            },
                        ],
                        "messages": [],
                    },
                },
                "errors": [],
            },
        }
    
    def _request(
        self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, json_data: Optional[Dict[str, Any]] = None
    ) -> requests.Response:
        """
        Esegue richiesta HTTP con gestione errori e retry.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: Endpoint path (es: "/messages/latest")
            params: Query parameters
            json_data: JSON body per POST/PUT
            
        Returns:
            Response object
            
        Raises:
            BookingAuthenticationError: 401
            BookingForbiddenError: 403
            BookingRateLimitError: 429
            BookingAPIError: Altri errori
        """
        if self.mock_mode:
            # Ritorna mock response
            mock_response = Mock(spec=requests.Response)
            mock_response.status_code = 200
            mock_response.json.return_value = self._get_mock_response(method, endpoint, params)
            mock_response.raise_for_status = lambda: None
            logger.debug(f"[MOCK] {method} {endpoint} -> mock response")
            return mock_response
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Accept-Version": self.api_version,
            "Content-Type": "application/json",
        }
        auth = requests.auth.HTTPBasicAuth(self.username, self.password)
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                auth=auth,
                params=params,
                json=json_data,
                timeout=30,
            )
            
            # Gestione errori HTTP
            if response.status_code == 401:
                raise BookingAuthenticationError(f"Authentication failed: {response.text}")
            elif response.status_code == 403:
                raise BookingForbiddenError(f"Access denied: {response.text}")
            elif response.status_code == 429:
                # Rate limit - exponential backoff
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limit exceeded, waiting {retry_after}s")
                time.sleep(retry_after)
                raise BookingRateLimitError(f"Rate limit exceeded: {response.text}")
            elif response.status_code >= 500:
                logger.error(f"Server error {response.status_code}: {response.text}")
                response.raise_for_status()
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise BookingAPIError(f"Request failed: {e}") from e
    
    def _get_mock_response(self, method: str, endpoint: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Ritorna mock response per endpoint."""
        if endpoint == "/messages/latest":
            return self._mock_responses["messages_latest"]
        elif "/conversations/type/reservation" in endpoint:
            reservation_id = params.get("conversation_reference") if params else None
            if reservation_id:
                conv = self._mock_responses["conversation_by_reservation"].copy()
                conv["data"]["conversation"]["conversation_reference"] = reservation_id
                return conv
        # Default empty response
        return {"data": {"ok": True}, "errors": [], "warnings": []}
    
    def get_latest_messages(self) -> Dict[str, Any]:
        """
        Recupera nuovi messaggi dalla coda.
        
        Returns:
            Response JSON con lista messaggi
        """
        response = self._request("GET", "/messages/latest")
        return response.json()
    
    def confirm_messages(self, number_of_messages: int) -> Dict[str, Any]:
        """
        Conferma recupero messaggi, rimuovendoli dalla coda.
        
        Args:
            number_of_messages: Numero messaggi da confermare
            
        Returns:
            Response JSON
        """
        params = {"number_of_messages": number_of_messages}
        response = self._request("PUT", "/messages", params=params)
        return response.json()
    
    def get_conversations(self, property_id: str, page_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Recupera tutte le conversazioni per una property.
        
        Args:
            property_id: ID della property
            page_id: ID pagina per paginazione (opzionale)
            
        Returns:
            Response JSON con lista conversazioni
        """
        params = {}
        if page_id:
            params["page_id"] = page_id
        response = self._request("GET", f"/properties/{property_id}/conversations", params=params)
        return response.json()
    
    def get_conversation_by_id(self, property_id: str, conversation_id: str, page_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Recupera una conversazione specifica per ID.
        
        Args:
            property_id: ID della property
            conversation_id: ID della conversazione
            page_id: ID pagina per paginazione (opzionale)
            
        Returns:
            Response JSON con conversazione completa
        """
        params = {}
        if page_id:
            params["page_id"] = page_id
        response = self._request("GET", f"/properties/{property_id}/conversations/{conversation_id}", params=params)
        return response.json()
    
    def get_conversation_by_reservation(
        self, property_id: str, reservation_id: str, page_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recupera conversazione per reservation_id.
        
        Args:
            property_id: ID della property
            reservation_id: ID della prenotazione
            page_id: ID pagina per paginazione (opzionale)
            
        Returns:
            Response JSON con conversazione
        """
        params = {"conversation_reference": reservation_id}
        if page_id:
            params["page_id"] = page_id
        response = self._request(
            "GET", f"/properties/{property_id}/conversations/type/reservation", params=params
        )
        return response.json()
    
    def send_message(
        self, property_id: str, conversation_id: str, content: str, attachment_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Invia un messaggio a una conversazione.
        
        Args:
            property_id: ID della property
            conversation_id: ID della conversazione
            content: Testo del messaggio
            attachment_ids: Lista ID allegati (opzionale)
            
        Returns:
            Response JSON con message_id
        """
        json_data = {
            "message": {
                "content": content,
                "attachment_ids": attachment_ids or [],
            }
        }
        response = self._request(
            "POST", f"/properties/{property_id}/conversations/{conversation_id}", json_data=json_data
        )
        return response.json()
    
    def mark_as_read(
        self, property_id: str, conversation_id: str, message_ids: List[str], participant_id: str
    ) -> Dict[str, Any]:
        """
        Marca messaggi come letti.
        
        Args:
            property_id: ID della property
            conversation_id: ID della conversazione
            message_ids: Lista ID messaggi da marcare
            participant_id: ID del participant (property)
            
        Returns:
            Response JSON
        """
        json_data = {"message_ids": message_ids, "participant_id": participant_id}
        response = self._request(
            "PUT",
            f"/properties/{property_id}/conversations/{conversation_id}/tags/message_read",
            json_data=json_data,
        )
        return response.json()

