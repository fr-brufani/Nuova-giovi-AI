from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from firebase_admin import firestore

from ..repositories.clients import ClientsRepository
from ..repositories.properties import PropertiesRepository
from ..repositories.reservations import ReservationsRepository
from ..services.gemini_service import GeminiService
from ..services.guest_message_pipeline import GuestMessageContext, GuestMessagePipelineService

logger = logging.getLogger(__name__)


class TestConversationService:
    """Service per gestire conversazioni di test che riusa la stessa logica di produzione."""

    def __init__(
        self,
        firestore_client: firestore.Client,
    ):
        self._firestore_client = firestore_client
        self._clients_repo = ClientsRepository(firestore_client)
        self._properties_repo = PropertiesRepository(firestore_client)
        self._reservations_repo = ReservationsRepository(firestore_client)
        self._guest_pipeline = GuestMessagePipelineService(firestore_client)
        self._gemini_service = GeminiService()

    def create_test_reservation(
        self,
        host_id: str,
        property_id: str,
        client_name: str,
        test_host_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> tuple[str, str, Optional[str]]:
        """
        Crea una reservation di test e il client associato.
        
        Returns:
            tuple[reservation_id, client_id]
        """
        try:
            # Verifica che la property esista e appartenga all'host
            property_data = self._properties_repo.get_by_id(property_id)
            if not property_data:
                raise ValueError(f"Property {property_id} non trovata")
            
            if property_data.get("hostId") != host_id:
                raise ValueError(f"Property {property_id} non appartiene all'host {host_id}")
            
            property_name = property_data.get("name", "Unknown Property")
            
            # Crea client test direttamente (non cerca per email per evitare conflitti)
            clients_ref = self._firestore_client.collection("clients")
            client_doc_ref = clients_ref.document()
            client_email = f"test-{uuid.uuid4().hex[:8]}@test.giovi.ai"
            
            client_data = {
                "name": client_name,
                "email": client_email.lower(),
                "role": "guest",
                "assignedHostId": host_id,
                "assignedPropertyId": property_id,
                "importedFrom": "test",
                "isTest": True,
                "createdAt": firestore.SERVER_TIMESTAMP,
                "lastUpdatedAt": firestore.SERVER_TIMESTAMP,
            }
            
            client_doc_ref.set(client_data)
            client_id = client_doc_ref.id
            
            # Aggiorna client con flag isTest
            client_doc = self._firestore_client.collection("clients").document(client_id)
            client_doc.update({"isTest": True})
            
            # Crea reservation test
            reservation_id = f"TEST-{uuid.uuid4().hex[:12].upper()}"
            
            # Default dates se non specificate
            if not start_date:
                start_date = datetime.now() + timedelta(days=1)
            if not end_date:
                end_date = start_date + timedelta(days=3)
            
            self._reservations_repo.upsert_reservation(
                reservation_id=reservation_id,
                host_id=host_id,
                property_id=property_id,
                property_name=property_name,
                client_id=client_id,
                client_name=client_name,
                start_date=start_date,
                end_date=end_date,
                status="confirmed",
                imported_from="test",
            )
            
            # Aggiorna reservation con flag isTest e testHostId
            reservations_ref = self._firestore_client.collection("reservations")
            query = (
                reservations_ref
                .where("reservationId", "==", reservation_id)
                .where("hostId", "==", host_id)
                .limit(1)
            )
            docs = list(query.get())
            reservation_doc_id = None
            if docs:
                docs[0].reference.update({
                    "isTest": True,
                    "testHostId": test_host_id,  # ID dell'utente test loggato
                })
                reservation_doc_id = docs[0].id
    
            # Aggiorna client con reservationId
            client_doc.update({"reservationId": reservation_id})
    
            logger.info(
                f"[TEST] Reservation test creata: reservationId={reservation_id}, "
                f"clientId={client_id}, propertyId={property_id}"
            )
    
            return reservation_id, client_id, reservation_doc_id
            
        except Exception as e:
            logger.error(f"[TEST] Errore creazione reservation test: {e}", exc_info=True)
            raise

    def send_test_message(
        self,
        host_id: str,
        property_id: str,
        client_id: str,
        reservation_id: str,
        message_text: str,
        attachments: Optional[list[dict]] = None,
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Invia un messaggio test e genera risposta AI usando la stessa logica di produzione.
        
        Args:
            host_id: ID host
            property_id: ID property
            client_id: ID client test
            reservation_id: ID reservation test
            message_text: Testo messaggio guest
            attachments: Lista allegati [{"url": str, "fileName": str, "fileType": str}]
        
        Returns:
            tuple[guest_message_id, ai_reply_text]
        """
        try:
            # Salva messaggio guest
            messages_ref = (
                self._firestore_client
                .collection("properties")
                .document(property_id)
                .collection("conversations")
                .document(client_id)
                .collection("messages")
            )
            
            message_data = {
                "sender": "guest",
                "text": message_text,
                "timestamp": firestore.SERVER_TIMESTAMP,
                "source": "test",
                "reservationId": reservation_id,
                "isTest": True,
            }
            
            if attachments:
                message_data["attachments"] = attachments
            
            # Aggiungi messaggio e ottieni ID
            # Firestore add() ritorna una tupla (timestamp, DocumentReference)
            _, message_doc_ref = messages_ref.add(message_data)
            guest_message_id = message_doc_ref.id
            
            logger.info(
                f"[TEST] Messaggio guest salvato: messageId={guest_message_id}, "
                f"propertyId={property_id}, clientId={client_id}"
            )
            
            # Estrai contesto usando la stessa logica di produzione
            # Costruiamo un contesto test riutilizzando la logica esistente
            property_data = self._properties_repo.get_by_id(property_id)
            property_name = property_data.get("name") if property_data else None
            
            client_data = self._clients_repo.get_by_id(client_id)
            client_name = client_data.get("name") if client_data else None
            client_email = client_data.get("email") if client_data else None
            
            # Recupera conversazione precedente (solo messaggi test per coerenza)
            conversation_history = self._guest_pipeline._get_conversation_history(property_id, client_id, is_test=True)
            
            # Crea contesto test
            context = GuestMessageContext(
                host_id=host_id,
                client_id=client_id,
                property_id=property_id,
                reservation_id=reservation_id,
                property_name=property_name,
                property_data=property_data or {},
                client_name=client_name,
                client_email=client_email,
                conversation_history=conversation_history,
                is_test=True,
            )
            
            # Genera risposta AI usando la stessa logica di produzione
            ai_reply = self._gemini_service.generate_reply(
                context=context,
                guest_message=message_text,
                attachments=attachments,
            )
            
            if ai_reply:
                # Salva risposta AI
                ai_message_data = {
                    "sender": "host_ai",
                    "text": ai_reply,
                    "timestamp": firestore.SERVER_TIMESTAMP,
                    "source": "ai_reply",
                    "reservationId": reservation_id,
                    "guestMessage": message_text,
                    "isTest": True,
                }
                
                messages_ref.add(ai_message_data)
                
                logger.info(
                    f"[TEST] Risposta AI salvata: propertyId={property_id}, "
                    f"clientId={client_id}, replyLength={len(ai_reply)}"
                )
                
                return guest_message_id, ai_reply
            else:
                logger.warning(f"[TEST] Nessuna risposta AI generata per messaggio {guest_message_id}")
                return guest_message_id, None
                
        except Exception as e:
            logger.error(f"[TEST] Errore invio messaggio test: {e}", exc_info=True)
            raise

    def get_conversation_messages(
        self,
        property_id: str,
        client_id: str,
        limit: int = 50,
    ) -> list[dict]:
        """
        Recupera messaggi della conversazione test.
        
        Returns:
            Lista messaggi ordinati per timestamp crescente
        """
        try:
            messages_ref = (
                self._firestore_client
                .collection("properties")
                .document(property_id)
                .collection("conversations")
                .document(client_id)
                .collection("messages")
            )
            
            # Recupera messaggi (includendo solo quelli test se necessario)
            query = messages_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)
            docs = list(query.get())
            
            # Inverti ordine (dal più vecchio al più recente) e filtra solo messaggi test
            messages = []
            for doc in reversed(docs):
                data = doc.to_dict()
                # Include solo messaggi test per coerenza
                if data.get("isTest", False):
                    messages.append({
                        "id": doc.id,
                        "sender": data.get("sender", "unknown"),
                        "text": data.get("text", ""),
                        "timestamp": data.get("timestamp"),
                        "attachments": data.get("attachments", []),
                        "imageUrl": data.get("imageUrl"),
                        "isTest": data.get("isTest", False),
                    })
            
            return messages
            
        except Exception as e:
            logger.error(f"[TEST] Errore recupero messaggi conversazione: {e}", exc_info=True)
            return []

    def list_test_reservations(
        self,
        host_id: str,
        property_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        Restituisce le prenotazioni di test per un host (e opzionalmente per una property specifica).
        DEPRECATED: Usa list_test_reservations_by_test_host invece.
        """
        try:
            reservations_ref = self._firestore_client.collection("reservations")
            query = (
                reservations_ref.where("hostId", "==", host_id).where("isTest", "==", True)
            )
            if property_id:
                query = query.where("propertyId", "==", property_id)
            docs = list(query.limit(limit).get())

            reservations = []
            for doc in docs:
                data = doc.to_dict()
                reservations.append(
                    {
                        "id": doc.id,
                        "reservationId": data.get("reservationId"),
                        "clientId": data.get("clientId"),
                        "clientName": data.get("clientName"),
                        "propertyId": data.get("propertyId"),
                        "propertyName": data.get("propertyName"),
                        "startDate": data.get("startDate"),
                        "endDate": data.get("endDate"),
                        "status": data.get("status"),
                        "createdAt": data.get("createdAt"),
                        "lastUpdatedAt": data.get("lastUpdatedAt"),
                    }
                )

            return reservations
        except Exception as e:
            logger.error(
                f"[TEST] Errore recupero prenotazioni di test per host={host_id}: {e}",
                exc_info=True,
            )
            return []
    
    def list_test_reservations_by_test_host(
        self,
        test_host_id: str,
        property_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        Restituisce le prenotazioni di test per un utente test loggato (filtrate per testHostId).
        """
        try:
            reservations_ref = self._firestore_client.collection("reservations")
            query = (
                reservations_ref.where("testHostId", "==", test_host_id).where("isTest", "==", True)
            )
            if property_id:
                query = query.where("propertyId", "==", property_id)
            docs = list(query.limit(limit).get())
            
            reservations = []
            for doc in docs:
                data = doc.to_dict()
                reservations.append(
                    {
                        "id": doc.id,
                        "reservationId": data.get("reservationId"),
                        "clientId": data.get("clientId"),
                        "clientName": data.get("clientName"),
                        "propertyId": data.get("propertyId"),
                        "propertyName": data.get("propertyName"),
                        "startDate": data.get("startDate"),
                        "endDate": data.get("endDate"),
                        "status": data.get("status"),
                        "createdAt": data.get("createdAt"),
                        "lastUpdatedAt": data.get("lastUpdatedAt"),
                    }
                )
            
            logger.info(
                f"[TEST] Trovate {len(reservations)} reservations test per testHostId={test_host_id}"
            )
            return reservations
            
        except Exception as e:
            logger.error(
                f"[TEST] Errore recupero prenotazioni di test per testHostId={test_host_id}: {e}",
                exc_info=True,
            )
            return []

