"""Client per Scidoo API."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Optional
from unittest.mock import Mock

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ...config.settings import get_settings
from ...models.scidoo_reservation import ScidooCustomer, ScidooGuest, ScidooReservation

logger = logging.getLogger(__name__)


class ScidooAPIError(Exception):
    """Errore generico API Scidoo."""
    pass


class ScidooAuthenticationError(ScidooAPIError):
    """Errore autenticazione API Scidoo (401/403)."""
    pass


class ScidooRateLimitError(ScidooAPIError):
    """Rate limit API Scidoo (429)."""
    pass


class ScidooReservationClient:
    """Client per Scidoo API con supporto mock mode."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        mock_mode: Optional[bool] = None,
    ) -> None:
        """
        Inizializza client Scidoo API.
        
        Args:
            api_key: API Key Scidoo (opzionale se mock_mode=True)
            base_url: Base URL API (default da settings)
            mock_mode: Se True, usa mock responses invece di chiamate reali
        """
        self._settings = get_settings()
        self.api_key = api_key
        self.base_url = base_url or self._settings.scidoo_api_base_url
        
        # Mock mode se non c'è API key o esplicitamente richiesto
        self.mock_mode = (
            mock_mode if mock_mode is not None else not self.api_key
        )
        
        if self.mock_mode:
            logger.info("[ScidooReservationClient] Initialized in MOCK MODE - using mock responses")
            self._init_mock_responses()
        else:
            logger.info(f"[ScidooReservationClient] Initialized in PRODUCTION MODE - API: {self.base_url}")
            self._init_session()
    
    def _init_session(self) -> None:
        """Inizializza session HTTP con retry logic."""
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
    
    def _init_mock_responses(self) -> None:
        """Inizializza mock responses per sviluppo senza credenziali."""
        self._mock_account_info = {
            "name": "Test Scidoo Account",
            "email": "test@scidoo.com",
            "website": "www.test.com",
            "account_id": "1",
            "properties": [
                {"id": 1, "name": "Test Property 1"},
                {"id": 2, "name": "Test Property 2"},
            ]
        }
        
        self._mock_room_types = [
            {
                "id": 1,
                "name": "Appartamento",
                "description": "Appartamento con vista",
                "size": 50,
                "capacity": 4,
                "additional_beds": 1,
                "images": []
            }
        ]
        
        # Mock reservations
        checkin = datetime.now() + timedelta(days=30)
        checkout = checkin + timedelta(days=3)
        self._mock_reservations = [
            {
                "id": "12345",
                "internal_id": "67890",
                "creation": checkin.isoformat(),
                "checkin_date": checkin.strftime("%Y-%m-%d"),
                "checkout_date": checkout.strftime("%Y-%m-%d"),
                "status": "confermata_manuale",
                "room_type_id": "1",
                "guest_count": 2,
                "customer": {
                    "first_name": "Mario",
                    "last_name": "Rossi",
                    "email": "mario.rossi@example.com",
                    "phone": "+393331234567"
                },
                "guests": []
            }
        ]
    
    def _request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[dict] = None
    ) -> requests.Response:
        """
        Esegue richiesta HTTP con gestione errori e retry.
        
        Args:
            method: HTTP method (POST)
            endpoint: Endpoint path (es: "/account/getInfo.php")
            data: JSON body per POST
            
        Returns:
            Response object con JSON content
            
        Raises:
            ScidooAuthenticationError: 401/403
            ScidooRateLimitError: 429
            ScidooAPIError: Altri errori
        """
        if self.mock_mode:
            # Ritorna mock response
            mock_response = Mock(spec=requests.Response)
            mock_response.status_code = 200
            
            if endpoint == "/account/getInfo.php":
                mock_response.json = lambda: self._mock_account_info
            elif endpoint == "/rooms/getRoomTypes.php":
                mock_response.json = lambda: self._mock_room_types
            elif endpoint == "/bookings/get.php":
                mock_response.json = lambda: self._mock_reservations
            
            mock_response.text = ""
            mock_response.content = b""
            mock_response.raise_for_status = lambda: None
            logger.debug(f"[MOCK] {method} {endpoint} -> mock response")
            return mock_response
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Api-Key": self.api_key,
        }
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                timeout=30,
            )
            
            # Gestione errori HTTP
            if response.status_code == 401 or response.status_code == 403:
                error_msg = response.json().get("message", response.text) if response.text else "Authentication failed"
                raise ScidooAuthenticationError(f"Authentication failed: {error_msg}")
            elif response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limit exceeded, waiting {retry_after}s")
                time.sleep(retry_after)
                raise ScidooRateLimitError(f"Rate limit exceeded")
            elif response.status_code >= 400:
                error_msg = response.json().get("message", response.text) if response.text else f"HTTP {response.status_code}"
                logger.error(f"API error {response.status_code}: {error_msg}")
                raise ScidooAPIError(f"API error {response.status_code}: {error_msg}")
            elif response.status_code >= 500:
                logger.error(f"Server error {response.status_code}: {response.text}")
                response.raise_for_status()
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise ScidooAPIError(f"Request failed: {e}") from e
    
    def get_account_info(self) -> dict:
        """
        Recupera informazioni account.
        
        Returns:
            dict con info account (name, email, properties)
        """
        response = self._request("POST", "/account/getInfo.php")
        return response.json()
    
    def get_room_types(self) -> list[dict]:
        """
        Recupera lista room types (categorie alloggio).
        
        Returns:
            Lista di room types
        """
        response = self._request("POST", "/rooms/getRoomTypes.php")
        return response.json()
    
    def get_reservations(
        self,
        last_modified: Optional[bool] = None,
        checkin_from: Optional[str] = None,
        checkin_to: Optional[str] = None,
        modified_from: Optional[str] = None,
        modified_to: Optional[str] = None,
        creation_from: Optional[str] = None,
        creation_to: Optional[str] = None,
        reservation_id: Optional[int] = None,
    ) -> list[ScidooReservation]:
        """
        Recupera prenotazioni.
        
        Args:
            last_modified: True per prenotazioni modificate dall'ultima richiesta
            checkin_from: Data checkin inizio (YYYY-MM-DD)
            checkin_to: Data checkin fine (YYYY-MM-DD)
            modified_from: Data modifica inizio (YYYY-MM-DD)
            modified_to: Data modifica fine (YYYY-MM-DD)
            creation_from: Data creazione inizio (YYYY-MM-DD)
            creation_to: Data creazione fine (YYYY-MM-DD)
            reservation_id: ID specifica prenotazione
        
        Returns:
            Lista di ScidooReservation
        """
        data = {}
        if last_modified is not None:
            data["last_modified"] = last_modified
        if checkin_from:
            data["checkin_from"] = checkin_from
        if checkin_to:
            data["checkin_to"] = checkin_to
        if modified_from:
            data["modified_from"] = modified_from
        if modified_to:
            data["modified_to"] = modified_to
        # Nota: creation_from/creation_to NON sono supportati da /bookings/get.php
        # Verranno usati per filtrare lato client dopo il recupero
        if reservation_id is not None:
            data["id"] = reservation_id
        
        # Se viene richiesto filtro per creation ma non ci sono altri filtri,
        # usiamo modified_from come approssimazione per limitare i risultati dall'API
        # (le prenotazioni create di recente sono anche quelle modificate di recente)
        filter_by_creation = creation_from or creation_to
        if filter_by_creation and not data:
            # Usa modified_from come fallback per limitare i risultati dall'API
            # Il filtro preciso per creation verrà fatto lato client
            if creation_from:
                data["modified_from"] = creation_from
                logger.info(f"[ScidooReservationClient] Usando modified_from={creation_from} come approssimazione per limitare risultati API, filtro preciso creation lato client")
        
        response = self._request("POST", "/bookings/get.php", data=data if data else None)
        raw_response_json = response.json()
        
        # Logging dettagliato per debug formato risposta
        logger.info(f"[ScidooReservationClient] Raw API response for /bookings/get.php: {str(raw_response_json)[:500]}...")
        logger.info(f"[ScidooReservationClient] Response type: {type(raw_response_json).__name__}")
        
        reservations_data = raw_response_json
        
        if isinstance(reservations_data, (list, tuple)):
            logger.info(f"[ScidooReservationClient] Response is array with {len(reservations_data)} elements")
            if len(reservations_data) > 0:
                logger.info(f"[ScidooReservationClient] First element type: {type(reservations_data[0]).__name__}")
                if isinstance(reservations_data[0], dict):
                    first_keys = list(reservations_data[0].keys())
                    logger.info(f"[ScidooReservationClient] First element keys: {first_keys}")
                    # Log esempio prima prenotazione per vedere tutti i campi
                    logger.info(f"[ScidooReservationClient] First reservation sample: {str(reservations_data[0])[:800]}")
        elif isinstance(reservations_data, dict):
            logger.info(f"[ScidooReservationClient] Response is dict with keys: {list(reservations_data.keys())}")
            # Cerca chiavi comuni per wrapper
            for key in ["bookings", "reservations", "data", "results"]:
                if key in reservations_data:
                    logger.info(f"[ScidooReservationClient] Found wrapper key '{key}', extracting data")
                    reservations_data = reservations_data[key]
                    # Dopo aver estratto il wrapper, logga le chiavi della prima prenotazione
                    if isinstance(reservations_data, (list, tuple)) and len(reservations_data) > 0:
                        if isinstance(reservations_data[0], dict):
                            first_keys = list(reservations_data[0].keys())
                            logger.info(f"[ScidooReservationClient] First reservation keys after unwrap: {first_keys}")
                            logger.info(f"[ScidooReservationClient] First reservation sample: {str(reservations_data[0])[:800]}")
                    break
        else:
            logger.warning(f"[ScidooReservationClient] Unexpected response type: {type(reservations_data).__name__}")
            # Log primi 500 caratteri della risposta raw
            try:
                raw_response = response.text[:500] if hasattr(response, 'text') else str(reservations_data)[:500]
                logger.warning(f"[ScidooReservationClient] Raw response preview: {raw_response}")
            except Exception:
                pass
        
        # Validazione tipo risposta
        if reservations_data is None:
            logger.warning("[ScidooReservationClient] Response is None, returning empty list")
            return []
        
        if not isinstance(reservations_data, (list, tuple)):
            logger.error(f"[ScidooReservationClient] Expected list/tuple, got {type(reservations_data).__name__}")
            return []
        
        if len(reservations_data) == 0:
            logger.info("[ScidooReservationClient] No reservations in response")
            return []
        
        # Parse reservations con gestione robusta
        reservations = []
        for idx, res_data in enumerate(reservations_data):
            try:
                # Verifica che res_data sia un dict
                if not isinstance(res_data, dict):
                    logger.warning(
                        f"[ScidooReservationClient] Skipping reservation at index {idx}: "
                        f"expected dict, got {type(res_data).__name__} (value: {str(res_data)[:100]})"
                    )
                    continue
                
                # Verifica che res_data non sia vuoto
                if not res_data:
                    logger.warning(f"[ScidooReservationClient] Skipping empty reservation at index {idx}")
                    continue
                
                reservation = self._parse_reservation(res_data)
                if reservation:
                    reservations.append(reservation)
                else:
                    logger.warning(f"[ScidooReservationClient] Failed to parse reservation at index {idx}: {res_data.get('id', 'unknown')}")
            except Exception as e:
                # Gestione errore robusta senza assumere che res_data sia dict
                res_id = "unknown"
                try:
                    if isinstance(res_data, dict):
                        res_id = res_data.get('id', res_data.get('internal_id', 'unknown'))
                    else:
                        res_id = str(res_data)[:50]
                except Exception:
                    pass
                
                logger.error(
                    f"[ScidooReservationClient] Error parsing reservation {res_id} at index {idx}: {e}",
                    exc_info=True
                )
                continue
        
        logger.info(f"[ScidooReservationClient] Successfully parsed {len(reservations)}/{len(reservations_data)} reservations")
        
        # Filtra per creation_from/creation_to lato client se richiesto
        # (l'API /bookings/get.php non supporta questi parametri)
        if creation_from or creation_to:
            filtered_reservations = []
            creation_from_date = None
            creation_to_date = None
            
            if creation_from:
                try:
                    creation_from_date = datetime.strptime(creation_from, "%Y-%m-%d").date()
                except ValueError:
                    logger.warning(f"[ScidooReservationClient] Invalid creation_from format: {creation_from}")
            
            if creation_to:
                try:
                    # Includi l'intera giornata
                    creation_to_date = datetime.strptime(creation_to, "%Y-%m-%d").date()
                except ValueError:
                    logger.warning(f"[ScidooReservationClient] Invalid creation_to format: {creation_to}")
            
            for reservation in reservations:
                if not reservation.creation:
                    # Se non abbiamo la data di creazione, includiamo la prenotazione
                    # (meglio includere che escludere)
                    filtered_reservations.append(reservation)
                    continue
                
                # Parse la data di creazione
                creation_raw = reservation.creation
                creation_datetime = None
                
                if isinstance(creation_raw, datetime):
                    creation_datetime = creation_raw
                elif isinstance(creation_raw, str):
                    # Prova a parsare come datetime
                    creation_datetime = self._parse_datetime(creation_raw)
                    if not creation_datetime:
                        # Fallback: prova come date
                        creation_datetime = self._parse_date(creation_raw)
                
                if not creation_datetime:
                    # Se non riusciamo a parsare, includiamo la prenotazione
                    filtered_reservations.append(reservation)
                    continue
                
                # Estrai solo la data (senza ora) per il confronto
                if hasattr(creation_datetime, 'date'):
                    creation_date_only = creation_datetime.date()
                elif isinstance(creation_datetime, datetime):
                    creation_date_only = creation_datetime.date()
                else:
                    creation_date_only = creation_datetime
                
                include = True
                if creation_from_date and creation_date_only < creation_from_date:
                    include = False
                
                if include and creation_to_date and creation_date_only > creation_to_date:
                    include = False
                
                if include:
                    filtered_reservations.append(reservation)
            
            logger.info(
                f"[ScidooReservationClient] Filtered by creation: {len(filtered_reservations)}/{len(reservations)} "
                f"reservations match creation_from={creation_from}, creation_to={creation_to}"
            )
            return filtered_reservations
        
        return reservations
    
    def _parse_reservation(self, data: dict) -> Optional[ScidooReservation]:
        """Parse singola prenotazione da JSON response."""
        if not isinstance(data, dict):
            logger.error(f"[ScidooReservationClient] _parse_reservation expects dict, got {type(data).__name__}")
            return None
        
        try:
            # Parse customer - gestisce None o dict vuoto
            customer_data = data.get("customer")
            if customer_data is None:
                customer_data = {}
            elif not isinstance(customer_data, dict):
                logger.warning(f"[ScidooReservationClient] Customer data is not dict: {type(customer_data).__name__}")
                customer_data = {}
            
            customer = ScidooCustomer(
                first_name=customer_data.get("first_name") if customer_data else None,
                last_name=customer_data.get("last_name") if customer_data else None,
                email=customer_data.get("email") if customer_data else None,
                phone=customer_data.get("phone") if customer_data else None,
            )
            
            # Parse guests - gestisce None, lista vuota o lista con elementi non-dict
            guests = []
            guests_data = data.get("guests")
            if guests_data and isinstance(guests_data, (list, tuple)):
                for idx, guest_data in enumerate(guests_data):
                    if isinstance(guest_data, dict):
                        try:
                            # Parse age - converte da stringa a int se necessario
                            age = guest_data.get("age")
                            age_int = None
                            if age is not None:
                                if isinstance(age, int):
                                    age_int = age
                                elif isinstance(age, str) and age.strip():
                                    try:
                                        age_int = int(age)
                                    except (ValueError, TypeError):
                                        logger.warning(f"[ScidooReservationClient] Invalid age value '{age}' for guest at index {idx}, skipping")
                                        age_int = None
                                elif isinstance(age, (float,)):
                                    age_int = int(age)
                            
                            guests.append(ScidooGuest(
                                first_name=guest_data.get("first_name"),
                                last_name=guest_data.get("last_name"),
                                age=age_int,
                                guest_type_id=guest_data.get("guest_type_id"),
                            ))
                        except Exception as e:
                            logger.warning(f"[ScidooReservationClient] Error parsing guest at index {idx}: {e}")
                    else:
                        logger.warning(f"[ScidooReservationClient] Guest at index {idx} is not dict: {type(guest_data).__name__}")
            
            # Parse dates - campi obbligatori
            checkin_date = self._parse_date(data.get("checkin_date"))
            checkout_date = self._parse_date(data.get("checkout_date"))
            creation = self._parse_datetime(data.get("creation"))
            
            # Validazione campi obbligatori
            if not checkin_date or not checkout_date:
                res_id = data.get('id') or data.get('internal_id', 'unknown')
                logger.warning(
                    f"[ScidooReservationClient] Missing dates for reservation {res_id}: "
                    f"checkin={data.get('checkin_date')}, checkout={data.get('checkout_date')}"
                )
                return None
            
            # Parse ID - gestisce diversi formati
            reservation_id = data.get("id")
            internal_id = data.get("internal_id", reservation_id)
            
            # Converti a stringa gestendo None e numeri
            id_str = str(reservation_id) if reservation_id is not None else ""
            internal_id_str = str(internal_id) if internal_id is not None else id_str
            
            # Parse room_type_id - può essere number o string
            room_type_id = data.get("room_type_id")
            room_type_id_str = str(room_type_id) if room_type_id is not None else ""
            
            # Parse guest_count - default 0 se mancante
            guest_count = data.get("guest_count", 0)
            if not isinstance(guest_count, (int, float)):
                try:
                    guest_count = int(guest_count) if guest_count else 0
                except (ValueError, TypeError):
                    guest_count = 0
            
            # Parse total_price - può essere None
            total_price = data.get("total_price")
            if total_price is not None:
                try:
                    total_price = float(total_price)
                except (ValueError, TypeError):
                    total_price = None
            
            return ScidooReservation(
                id=id_str,
                internal_id=internal_id_str,
                room_type_id=room_type_id_str,
                checkin_date=checkin_date,
                checkout_date=checkout_date,
                status=data.get("status", "confermata_manuale"),
                guest_count=guest_count,
                customer=customer,
                guests=guests,
                creation=creation,
                total_price=total_price,
                currency=data.get("currency", "EUR"),
            )
        except Exception as e:
            res_id = data.get('id') or data.get('internal_id', 'unknown') if isinstance(data, dict) else 'unknown'
            logger.error(f"[ScidooReservationClient] Error parsing reservation {res_id}: {e}", exc_info=True)
            return None
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string YYYY-MM-DD."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None
    
    def _parse_datetime(self, datetime_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string YYYY-MM-DD HH:MM."""
        if not datetime_str:
            return None
        try:
            # Prova formato YYYY-MM-DD HH:MM
            return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        except ValueError:
            try:
                # Prova formato ISO
                return datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
            except ValueError:
                return None

