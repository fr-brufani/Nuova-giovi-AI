"""Client per Booking.com Reservation API (OTA XML)."""

from __future__ import annotations

import logging
import time
from typing import Optional
from unittest.mock import Mock

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ...config.settings import get_settings
from .booking_messaging_client import (
    BookingAPIError,
    BookingAuthenticationError,
    BookingForbiddenError,
    BookingRateLimitError,
)

logger = logging.getLogger(__name__)


class BookingReservationClient:
    """Client per Booking.com Reservation API (OTA XML) con supporto mock mode."""

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        base_url: Optional[str] = None,
        mock_mode: Optional[bool] = None,
    ) -> None:
        """
        Inizializza client Reservation API.
        
        Args:
            username: Username Machine Account (opzionale se mock_mode=True)
            password: Password Machine Account (opzionale se mock_mode=True)
            base_url: Base URL API (default da settings)
            mock_mode: Se True, usa mock responses invece di chiamate reali
        """
        self._settings = get_settings()
        self.username = username or self._settings.booking_api_username
        self.password = password or self._settings.booking_api_password
        self.base_url = base_url or self._settings.booking_reservation_api_base_url
        
        # Mock mode se non ci sono credenziali o esplicitamente richiesto
        self.mock_mode = (
            mock_mode if mock_mode is not None else not (self.username and self.password)
        )
        
        if self.mock_mode:
            logger.info("[BookingReservationClient] Initialized in MOCK MODE - using mock XML responses")
            self._init_mock_responses()
        else:
            logger.info(f"[BookingReservationClient] Initialized in PRODUCTION MODE - API: {self.base_url}")
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
        """Inizializza mock XML responses per sviluppo senza credenziali."""
        self._mock_xml_response = """<?xml version="1.0" encoding="UTF-8"?>
<OTA_HotelResNotifRQ xmlns="http://www.opentravel.org/OTA/2003/05" TimeStamp="2025-01-15T10:00:00+00:00" Target="Production" Version="2.001">
    <HotelReservations>
        <HotelReservation>
            <RoomStays>
                <RoomStay IndexNumber="460">
                    <RoomTypes>
                        <RoomType RoomTypeCode="1296364403">
                            <RoomDescription Name="Test Room">
                                <Text>Test room description</Text>
                            </RoomDescription>
                        </RoomType>
                    </RoomTypes>
                    <RoomRates>
                        <RoomRate EffectiveDate="2025-03-29" RatePlanCode="49111777">
                            <Rates>
                                <Rate>
                                    <Total AmountBeforeTax="500" CurrencyCode="EUR" DecimalPlaces="2"/>
                                </Rate>
                            </Rates>
                        </RoomRate>
                    </RoomRates>
                    <GuestCounts>
                        <GuestCount Count="2" AgeQualifyingCode="10"/>
                    </GuestCounts>
                    <BasicPropertyInfo HotelCode="8011855"/>
                </RoomStay>
            </RoomStays>
            <ResGlobalInfo>
                <HotelReservationIDs>
                    <HotelReservationID ResID_Value="4705950059" ResID_Date="2025-01-15T10:00:00"/>
                </HotelReservationIDs>
                <Profiles>
                    <ProfileInfo>
                        <Profile>
                            <Customer>
                                <PersonName>
                                    <GivenName>Test</GivenName>
                                    <Surname>Guest</Surname>
                                </PersonName>
                                <Telephone PhoneNumber="+39 333 1234567"/>
                                <Email>test.guest@example.com</Email>
                            </Customer>
                        </Profile>
                    </ProfileInfo>
                </Profiles>
                <Total AmountBeforeTax="500" CurrencyCode="EUR" DecimalPlaces="2"/>
            </ResGlobalInfo>
        </HotelReservation>
    </HotelReservations>
</OTA_HotelResNotifRQ>"""
        
        self._mock_ack_response = """<?xml version="1.0" encoding="UTF-8"?>
<OTA_HotelResNotifRS xmlns="http://www.opentravel.org/OTA/2003/05" TimeStamp="2025-01-15T10:00:00+00:00">
    <Success/>
</OTA_HotelResNotifRS>"""
    
    def _request(
        self, method: str, endpoint: str, params: Optional[dict] = None, data: Optional[str] = None
    ) -> requests.Response:
        """
        Esegue richiesta HTTP con gestione errori e retry.
        
        Args:
            method: HTTP method (GET, POST)
            endpoint: Endpoint path (es: "/OTA_HotelResNotif")
            params: Query parameters
            data: XML body per POST
            
        Returns:
            Response object con XML content
            
        Raises:
            BookingAuthenticationError: 401
            BookingForbiddenError: 403
            BookingRateLimitError: 429
            BookingAPIError: Altri errori
        """
        if self.mock_mode:
            # Ritorna mock XML response
            mock_response = Mock(spec=requests.Response)
            mock_response.status_code = 200
            if method == "GET":
                mock_response.text = self._mock_xml_response
            else:
                mock_response.text = self._mock_ack_response
            mock_response.content = mock_response.text.encode("utf-8")
            mock_response.raise_for_status = lambda: None
            logger.debug(f"[MOCK] {method} {endpoint} -> mock XML response")
            return mock_response
        
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/xml"}
        auth = requests.auth.HTTPBasicAuth(self.username, self.password)
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                auth=auth,
                params=params,
                data=data,
                timeout=30,
            )
            
            # Gestione errori HTTP (stessa logica di Messaging Client)
            if response.status_code == 401:
                raise BookingAuthenticationError(f"Authentication failed: {response.text}")
            elif response.status_code == 403:
                raise BookingForbiddenError(f"Access denied: {response.text}")
            elif response.status_code == 429:
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
    
    def get_new_reservations(
        self, hotel_ids: Optional[str] = None, last_change: Optional[str] = None, limit: Optional[int] = None
    ) -> str:
        """
        Recupera nuove prenotazioni (OTA XML).
        
        Args:
            hotel_ids: Lista property IDs separati da virgola (opzionale)
            last_change: Data/ora formato YYYY-MM-DD HH:MM:SS (opzionale)
            limit: Numero massimo prenotazioni (10-200, opzionale)
            
        Returns:
            XML string con prenotazioni
        """
        params = {}
        if hotel_ids:
            params["hotel_ids"] = hotel_ids
        if last_change:
            params["last_change"] = last_change
        if limit:
            params["limit"] = limit
        
        response = self._request("GET", "OTA_HotelResNotif", params=params)
        return response.text
    
    def acknowledge_new_reservations(self, reservations_xml: str) -> str:
        """
        Conferma processamento nuove prenotazioni.
        
        Args:
            reservations_xml: XML delle prenotazioni da confermare
            
        Returns:
            XML response con conferma
        """
        response = self._request("POST", "OTA_HotelResNotif", data=reservations_xml)
        return response.text
    
    def get_modified_reservations(
        self, hotel_ids: Optional[str] = None, last_change: Optional[str] = None, limit: Optional[int] = None
    ) -> str:
        """
        Recupera prenotazioni modificate o cancellate (OTA XML).
        
        Args:
            hotel_ids: Lista property IDs separati da virgola (opzionale)
            last_change: Data/ora formato YYYY-MM-DD HH:MM:SS (opzionale)
            limit: Numero massimo prenotazioni (10-200, opzionale)
            
        Returns:
            XML string con prenotazioni modificate/cancellate
        """
        params = {}
        if hotel_ids:
            params["hotel_ids"] = hotel_ids
        if last_change:
            params["last_change"] = last_change
        if limit:
            params["limit"] = limit
        
        response = self._request("GET", "OTA_HotelResModifyNotif", params=params)
        return response.text
    
    def acknowledge_modified_reservations(self, reservations_xml: str) -> str:
        """
        Conferma processamento prenotazioni modificate/cancellate.
        
        Args:
            reservations_xml: XML delle prenotazioni da confermare
            
        Returns:
            XML response con conferma
        """
        response = self._request("POST", "OTA_HotelResModifyNotif", data=reservations_xml)
        return response.text

