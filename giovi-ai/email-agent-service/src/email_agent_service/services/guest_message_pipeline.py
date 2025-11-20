from __future__ import annotations

import logging
from typing import Optional

from firebase_admin import firestore

from ..models import ParsedEmail
from ..repositories import ClientsRepository, PropertiesRepository, ReservationsRepository

logger = logging.getLogger(__name__)


class GuestMessageContext:
    """Contesto estratto per un messaggio guest."""

    def __init__(
        self,
        host_id: str,
        client_id: str,
        property_id: str,
        reservation_id: str,
        property_name: Optional[str] = None,
        client_name: Optional[str] = None,
        client_email: Optional[str] = None,
        conversation_history: Optional[list[dict]] = None,
    ):
        self.host_id = host_id
        self.client_id = client_id
        self.property_id = property_id
        self.reservation_id = reservation_id
        self.property_name = property_name
        self.client_name = client_name
        self.client_email = client_email
        self.conversation_history = conversation_history or []


class GuestMessagePipelineService:
    """Service per processare messaggi guest e preparare contesto per AI reply."""

    def __init__(
        self,
        firestore_client: firestore.Client,
    ):
        self._firestore_client = firestore_client
        self._clients_repo = ClientsRepository(firestore_client)
        self._properties_repo = PropertiesRepository(firestore_client)
        self._reservations_repo = ReservationsRepository(firestore_client)

    def should_process_message(
        self,
        parsed_email: ParsedEmail,
        host_id: str,
        is_new_reservation: bool = False,
    ) -> tuple[bool, Optional[str]]:
        """
        Verifica se un messaggio guest deve essere processato (auto-reply abilitato).
        
        Args:
            parsed_email: Email parsata
            host_id: ID dell'host
            is_new_reservation: Se True, il messaggio è allegato a una nuova prenotazione
        
        Returns:
            tuple[should_process, client_id]: True se deve essere processato, ID del cliente
        """
        if parsed_email.kind not in ["booking_message", "airbnb_message"]:
            # Se è una conferma con messaggio, gestiscila come nuovo messaggio da prenotazione
            if parsed_email.kind in ["airbnb_confirmation", "scidoo_confirmation"] and parsed_email.guest_message:
                is_new_reservation = True
            else:
                return False, None

        if not parsed_email.guest_message:
            logger.warning(f"[PIPELINE] Messaggio guest senza guestMessage: {parsed_email.metadata.gmail_message_id}")
            return False, None

        reservation_id = parsed_email.guest_message.reservation_id
        thread_id = parsed_email.guest_message.thread_id
        guest_email = parsed_email.guest_message.guest_email
        source = parsed_email.guest_message.source

        # Trova il cliente usando reservationId, threadId (per Airbnb) o guestEmail
        client_id = self._find_client_id(host_id, reservation_id, guest_email, thread_id=thread_id, source=source)

        if not client_id:
            logger.info(
                f"[PIPELINE] Cliente non trovato per reservationId={reservation_id}, "
                f"guestEmail={guest_email}, hostId={host_id}"
            )
            return False, None

        # Se è un messaggio da nuova prenotazione, verifica il flag dell'host
        if is_new_reservation:
            host_auto_reply_enabled = self._check_host_auto_reply_to_new_reservations(host_id)
            if not host_auto_reply_enabled:
                logger.info(f"[PIPELINE] Auto-reply a nuove prenotazioni disabilitato per host {host_id}")
                return False, client_id

        # Verifica autoReplyEnabled del cliente
        auto_reply_enabled = self._check_auto_reply_enabled(client_id)

        if not auto_reply_enabled:
            logger.info(f"[PIPELINE] Auto-reply disabilitato per cliente {client_id}")
            return False, client_id

        logger.info(f"[PIPELINE] ✅ Messaggio guest da processare: clientId={client_id}, reservationId={reservation_id}, isNewReservation={is_new_reservation}")
        return True, client_id

    def extract_context(
        self,
        parsed_email: ParsedEmail,
        host_id: str,
        client_id: str,
    ) -> Optional[GuestMessageContext]:
        """
        Estrae il contesto completo per un messaggio guest.
        
        Returns:
            GuestMessageContext con tutte le informazioni necessarie per generare risposta AI
        """
        if not parsed_email.guest_message:
            return None

        reservation_id = parsed_email.guest_message.reservation_id
        thread_id = parsed_email.guest_message.thread_id
        source = parsed_email.guest_message.source

        # Trova la prenotazione (usa threadId se reservationId è "unknown" per Airbnb)
        reservation = self._find_reservation(host_id, reservation_id, thread_id=thread_id, source=source)
        if not reservation:
            logger.warning(f"[PIPELINE] Prenotazione non trovata: reservationId={reservation_id}, hostId={host_id}")
            return None

        property_id = reservation.get("propertyId")
        if not property_id:
            logger.warning(f"[PIPELINE] Prenotazione senza propertyId: {reservation_id}")
            return None

        # Trova la property
        property_data = self._find_property(property_id)
        property_name = property_data.get("name") if property_data else None

        # Trova il cliente
        client_data = self._find_client(client_id)
        client_name = client_data.get("name") if client_data else None
        client_email = client_data.get("email") if client_data else None

        # Recupera conversazione precedente
        conversation_history = self._get_conversation_history(property_id, client_id)

        return GuestMessageContext(
            host_id=host_id,
            client_id=client_id,
            property_id=property_id,
            reservation_id=reservation_id,
            property_name=property_name,
            client_name=client_name,
            client_email=client_email,
            conversation_history=conversation_history,
        )

    def _find_client_id(
        self,
        host_id: str,
        reservation_id: Optional[str],
        guest_email: Optional[str],
        thread_id: Optional[str] = None,
        source: Optional[str] = None,
    ) -> Optional[str]:
        """
        Trova l'ID del cliente usando reservationId, threadId (per Airbnb) o guestEmail.
        
        Flusso:
        1. Se abbiamo reservationId, cerca PRIMA nelle reservations
        2. Per Airbnb: se reservationId è "unknown", usa threadId per cercare la reservation
        3. Se trovi la reservation, estrai il clientId da lì
        4. Se non c'è clientId nella reservation, cerca per email nei clients
        5. Fallback: cerca direttamente nei clients per reservationId o email
        """
        # Passo 1: Cerca la reservation usando reservationId o threadId (per Airbnb)
        reservation = None
        if reservation_id and reservation_id != "unknown":
            reservation = self._find_reservation(host_id, reservation_id, thread_id=thread_id, source=source)
        elif source == "airbnb" and thread_id:
            # Per Airbnb: se reservationId è "unknown", cerca usando threadId
            reservation = self._find_reservation(host_id, "unknown", thread_id=thread_id, source=source)
        
        if reservation:
            # Passo 2: Estrai clientId dalla reservation se presente
            client_id_from_reservation = reservation.get("clientId")
            if client_id_from_reservation:
                # Verifica che il client esista ancora
                client_doc = self._firestore_client.collection("clients").document(client_id_from_reservation).get()
                if client_doc.exists:
                    logger.info(f"[PIPELINE] ClientId trovato dalla reservation: {client_id_from_reservation}")
                    return client_id_from_reservation
            
            # Se la reservation esiste ma non ha clientId, usa guestEmail per cercare
            # (fallback al passo 3)
        
        # Passo 3: Cerca per email nei clients
        clients_ref = self._firestore_client.collection("clients")
        if guest_email:
            query = (
                clients_ref
                .where("email", "==", guest_email.lower())
                .where("assignedHostId", "==", host_id)
                .limit(1)
            )
            docs = list(query.get())
            if docs:
                return docs[0].id
        
        # Passo 4: Fallback - cerca direttamente nei clients per reservationId
        if reservation_id and reservation_id != "unknown":
            query = (
                clients_ref
                .where("reservationId", "==", reservation_id)
                .where("assignedHostId", "==", host_id)
                .limit(1)
            )
            docs = list(query.get())
            if docs:
                return docs[0].id

        return None

    def _check_auto_reply_enabled(self, client_id: str) -> bool:
        """Verifica se auto-reply è abilitato per il cliente."""
        try:
            client_doc = self._firestore_client.collection("clients").document(client_id).get()
            if not client_doc.exists:
                return False

            client_data = client_doc.to_dict()
            # Default: False per nuovi clienti
            return client_data.get("autoReplyEnabled", False)
        except Exception as e:
            logger.error(f"[PIPELINE] Errore verifica autoReplyEnabled per {client_id}: {e}", exc_info=True)
            return False

    def _check_host_auto_reply_to_new_reservations(self, host_id: str) -> bool:
        """Verifica se l'host ha abilitato auto-reply per messaggi in nuove prenotazioni."""
        try:
            host_doc = self._firestore_client.collection("hosts").document(host_id).get()
            if not host_doc.exists:
                return False

            host_data = host_doc.to_dict()
            # Default: False (non abilitato di default)
            return host_data.get("autoReplyToNewReservations", False)
        except Exception as e:
            logger.error(f"[PIPELINE] Errore verifica autoReplyToNewReservations per host {host_id}: {e}", exc_info=True)
            return False

    def _find_reservation(self, host_id: str, reservation_id: str, thread_id: Optional[str] = None, source: Optional[str] = None) -> Optional[dict]:
        """
        Trova la prenotazione usando reservationId o threadId (per Airbnb).
        
        Per Airbnb: se reservationId è "unknown", cerca usando threadId.
        Per Booking: usa sempre reservationId (o voucherId).
        """
        try:
            reservations_ref = self._firestore_client.collection("reservations")
            
            # Se abbiamo reservationId valido, cerca per quello
            if reservation_id and reservation_id != "unknown":
                query = (
                    reservations_ref
                    .where("reservationId", "==", reservation_id)
                    .where("hostId", "==", host_id)
                    .limit(1)
                )
                docs = list(query.get())
                if docs:
                    return docs[0].to_dict()
            
            # Per Airbnb: se reservationId è "unknown" e abbiamo threadId, cerca per threadId
            if source == "airbnb" and thread_id:
                query = (
                    reservations_ref
                    .where("threadId", "==", thread_id)
                    .where("hostId", "==", host_id)
                    .limit(1)
                )
                docs = list(query.get())
                if docs:
                    logger.info(f"[PIPELINE] Reservation trovata tramite threadId: {thread_id}")
                    return docs[0].to_dict()
        except Exception as e:
            logger.error(f"[PIPELINE] Errore ricerca prenotazione reservationId={reservation_id}, threadId={thread_id}: {e}", exc_info=True)

        return None

    def _find_property(self, property_id: str) -> Optional[dict]:
        """Trova la property."""
        try:
            property_doc = self._firestore_client.collection("properties").document(property_id).get()
            if property_doc.exists:
                return property_doc.to_dict()
        except Exception as e:
            logger.error(f"[PIPELINE] Errore ricerca property {property_id}: {e}", exc_info=True)

        return None

    def _find_client(self, client_id: str) -> Optional[dict]:
        """Trova il cliente."""
        try:
            client_doc = self._firestore_client.collection("clients").document(client_id).get()
            if client_doc.exists:
                return client_doc.to_dict()
        except Exception as e:
            logger.error(f"[PIPELINE] Errore ricerca cliente {client_id}: {e}", exc_info=True)

        return None

    def save_guest_message(
        self,
        context: GuestMessageContext,
        parsed_email: ParsedEmail,
        gmail_message_id: str,
    ) -> None:
        """
        Salva il messaggio guest nella conversazione.
        
        La conversazione è salvata in: properties/{propertyId}/conversations/{clientId}/messages
        """
        if not parsed_email.guest_message:
            return

        try:
            messages_ref = (
                self._firestore_client
                .collection("properties")
                .document(context.property_id)
                .collection("conversations")
                .document(context.client_id)
                .collection("messages")
            )

            # Salva il messaggio
            message_data = {
                "sender": "guest",
                "text": parsed_email.guest_message.message,
                "timestamp": parsed_email.metadata.received_at or firestore.SERVER_TIMESTAMP,
                "source": parsed_email.guest_message.source,
                "gmailMessageId": gmail_message_id,
                "reservationId": context.reservation_id,
            }

            messages_ref.add(message_data)
            logger.info(f"[PIPELINE] Messaggio guest salvato in conversazione: property={context.property_id}, client={context.client_id}")
        except Exception as e:
            logger.error(f"[PIPELINE] Errore salvataggio messaggio guest: {e}", exc_info=True)

    def _get_conversation_history(
        self,
        property_id: str,
        client_id: str,
    ) -> list[dict]:
        """
        Recupera la storia della conversazione per questo cliente e property.
        
        La conversazione è salvata in: properties/{propertyId}/conversations/{clientId}/messages
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

            # Recupera ultimi 10 messaggi (per contesto)
            query = messages_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(10)
            docs = list(query.get())

            # Inverti ordine (dal più vecchio al più recente)
            messages = []
            for doc in reversed(docs):
                data = doc.to_dict()
                messages.append({
                    "sender": data.get("sender", "unknown"),
                    "text": data.get("text", ""),
                    "timestamp": data.get("timestamp"),
                })

            return messages
        except Exception as e:
            logger.warning(f"[PIPELINE] Errore recupero conversazione per property={property_id}, client={client_id}: {e}")
            return []

