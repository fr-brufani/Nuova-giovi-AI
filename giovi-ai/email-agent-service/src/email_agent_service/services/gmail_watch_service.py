from __future__ import annotations

import logging
from typing import Optional

from firebase_admin import firestore

from ..models import ParsedEmail
from ..parsers import EmailParsingEngine
from ..parsers.engine import decode_gmail_raw
from ..repositories import HostEmailIntegrationRepository, ProcessedMessageRepository
from ..services.gmail_service import GmailService
from ..services.persistence_service import PersistenceService
from ..services.guest_message_pipeline import GuestMessageContext, GuestMessagePipelineService
from ..services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class GmailWatchService:
    """Service per processare notifiche Gmail Watch e nuove email."""

    def __init__(
        self,
        gmail_service: GmailService,
        integration_repository: HostEmailIntegrationRepository,
        processed_repository: ProcessedMessageRepository,
        parsing_engine: EmailParsingEngine,
        persistence_service: PersistenceService,
        firestore_client: firestore.Client,
    ):
        self._gmail_service = gmail_service
        self._integration_repository = integration_repository
        self._processed_repository = processed_repository
        self._parsing_engine = parsing_engine
        self._persistence_service = persistence_service
        self._firestore_client = firestore_client
        self._guest_pipeline = GuestMessagePipelineService(firestore_client)
        self._gemini_service = GeminiService()

    def process_new_emails(self, email: str, notified_history_id: str) -> None:
        """
        Processa nuove email da una notifica Gmail Watch.
        
        Args:
            email: Email dell'integrazione Gmail
            notified_history_id: History ID ricevuto dalla notifica Pub/Sub
        """
        logger.info(f"[WATCH] Processamento nuove email per {email}, historyId: {notified_history_id}")

        # Recupera integrazione
        integration = self._integration_repository.get_by_email(email)
        if not integration:
            logger.error(f"[WATCH] Integrazione non trovata per {email}")
            return

        # Recupera host_id e pmsProvider dalla collezione hosts
        host_id = integration.host_id
        pms_provider = self._get_pms_provider_from_host(host_id)
        
        logger.info(f"[WATCH] Host ID: {host_id}, PMS Provider: {pms_provider}")

        # Recupera lastHistoryIdProcessed
        start_history_id = integration.last_history_id_processed or (
            integration.watch_subscription.get("historyId") if integration.watch_subscription else None
        )
        
        if not start_history_id:
            # Fallback: usa notified_history_id come punto di partenza
            # Questo può causare la perdita di alcune email, ma è meglio di non processare nulla
            logger.warning(
                f"[WATCH] Missing startHistoryId per {email}. "
                f"Usando notified_history_id={notified_history_id} come fallback. "
                f"Alcune email potrebbero essere perse. Si consiglia di riattivare il watch dal frontend."
            )
            start_history_id = notified_history_id
            # Salva questo historyId come lastHistoryIdProcessed per evitare il problema in futuro
            # Usiamo un expiration temporaneo (non verrà usato, ma serve per la struttura)
            try:
                from datetime import datetime, timezone
                # Calcola expiration 7 giorni da ora in millisecondi
                expiration_7days = int((datetime.now(timezone.utc).timestamp() + (7 * 24 * 60 * 60)) * 1000)
                self._integration_repository.update_watch_subscription(
                    email=email,
                    history_id=notified_history_id,
                    expiration_ms=expiration_7days,
                )
                logger.info(f"[WATCH] Salvato fallback historyId={notified_history_id} come lastHistoryIdProcessed")
            except Exception as e:
                logger.error(f"[WATCH] Errore salvataggio fallback historyId: {e}", exc_info=True)

        # Verifica che notified_history_id sia maggiore di start_history_id
        try:
            if int(notified_history_id) <= int(start_history_id):
                logger.info(f"[WATCH] History ID già processato: {notified_history_id} <= {start_history_id}")
                return
        except (ValueError, TypeError):
            logger.warning(f"[WATCH] History ID non numerici, procedo comunque")

        # Recupera history da Gmail
        try:
            history_response = self._gmail_service.get_history(integration, start_history_id)
        except Exception as e:
            logger.error(f"[WATCH] Errore recupero history per {email}: {e}", exc_info=True)
            return

        history_records = history_response.get("history", [])
        if not history_records:
            logger.info(f"[WATCH] Nessuna nuova email trovata per {email}")
            return

        logger.info(f"[WATCH] Trovate {len(history_records)} record history per {email}")

        # Processa ogni nuova email
        processed_count = 0
        skipped_count = 0

        for record in history_records:
            messages_added = record.get("messagesAdded", [])
            for msg_added in messages_added:
                message = msg_added.get("message")
                if not message:
                    continue

                message_id = message.get("id")
                label_ids = message.get("labelIds", [])

                # Processa solo email in INBOX
                if "INBOX" not in label_ids:
                    continue

                # Verifica se già processata
                if self._processed_repository.was_processed(email, message_id):
                    skipped_count += 1
                    continue

                # Estrai e processa email
                try:
                    payload = self._gmail_service.get_message_raw(integration, message_id)
                    raw_data = decode_gmail_raw(payload["raw"])
                    snippet = payload.get("snippet")

                    # Parsa email
                    parsed = self._parsing_engine.parse(
                        message_id=message_id,
                        raw_payload=raw_data,
                        snippet=snippet,
                    )

                    logger.info(f"[WATCH] Email {message_id} parsata: kind={parsed.kind}, sender={parsed.metadata.sender}")

                    # Verifica se email è rilevante (filtro in base a pmsProvider)
                    if not self._is_email_relevant(parsed, pms_provider):
                        logger.debug(f"[WATCH] Email {message_id} non rilevante per pmsProvider={pms_provider}, skip")
                        # Marca come processata comunque per evitare riprocessamento
                        self._processed_repository.mark_processed(
                            email,
                            message_id,
                            history_id=notified_history_id,
                        )
                        skipped_count += 1
                        continue

                    # Salva in Firestore (solo se è rilevante)
                    if parsed.kind != "unhandled":
                        save_result = self._persistence_service.save_parsed_email(
                            parsed_email=parsed,
                            host_id=host_id,
                        )
                        if save_result.get("saved"):
                            logger.info(f"[WATCH] ✅ Email salvata: {message_id}")
                        else:
                            logger.warning(f"[WATCH] ⚠️ Salvataggio fallito: {save_result.get('reason')}")

                    # Step 6: Processa messaggi guest per AI reply (se auto-reply abilitato)
                    if parsed.kind in ["booking_message", "airbnb_message"]:
                        should_process, client_id = self._guest_pipeline.should_process_message(
                            parsed_email=parsed,
                            host_id=host_id,
                        )
                        if should_process and client_id:
                            context = self._guest_pipeline.extract_context(
                                parsed_email=parsed,
                                host_id=host_id,
                                client_id=client_id,
                            )
                            if context:
                                # Salva il messaggio nella conversazione
                                self._guest_pipeline.save_guest_message(
                                    context=context,
                                    parsed_email=parsed,
                                    gmail_message_id=message_id,
                                )
                                
                                logger.info(
                                    f"[WATCH] 📧 Messaggio guest pronto per AI reply: "
                                    f"clientId={context.client_id}, reservationId={context.reservation_id}"
                                )
                                
                                # Step 7: Chiamare Gemini AI con questo contesto
                                if parsed.guest_message:
                                    ai_reply = self._gemini_service.generate_reply(
                                        context=context,
                                        guest_message=parsed.guest_message.message,
                                    )
                                    
                                    if ai_reply:
                                        logger.info(f"[WATCH] ✅ Risposta AI generata ({len(ai_reply)} caratteri)")
                                        
                                        # Step 8: Inviare risposta email
                                        try:
                                            # Estrai informazioni per threading
                                            reply_to = parsed.guest_message.reply_to
                                            original_subject = parsed.metadata.subject or "Messaggio"
                                            
                                            # Estrai Message-ID originale se disponibile
                                            original_message_id = parsed.metadata.gmail_message_id
                                            
                                            # Invia risposta
                                            send_result = self._gmail_service.send_reply(
                                                integration=integration,
                                                to_email=reply_to or parsed.metadata.sender or "",
                                                subject=original_subject,
                                                body=ai_reply,
                                                reply_to=reply_to,
                                                in_reply_to=original_message_id,
                                                references=original_message_id,
                                            )
                                            
                                            logger.info(
                                                f"[WATCH] ✅ Email risposta inviata: "
                                                f"messageId={send_result.get('messageId')}, "
                                                f"threadId={send_result.get('threadId')}"
                                            )
                                            
                                            # Salva risposta AI in Firestore
                                            self._save_ai_response(
                                                context=context,
                                                guest_message=parsed.guest_message.message,
                                                ai_reply=ai_reply,
                                                gmail_message_id=message_id,
                                                reply_message_id=send_result.get("messageId"),
                                            )
                                            
                                        except Exception as e:
                                            logger.error(f"[WATCH] ❌ Errore invio email risposta: {e}", exc_info=True)
                                    else:
                                        logger.warning("[WATCH] ⚠️ Impossibile generare risposta AI")

                    # Marca come processata
                    self._processed_repository.mark_processed(
                        email,
                        message_id,
                        history_id=notified_history_id,
                    )
                    processed_count += 1

                except Exception as e:
                    logger.error(f"[WATCH] Errore processamento email {message_id}: {e}", exc_info=True)
                    # Marca come processata anche in caso di errore per evitare loop
                    self._processed_repository.mark_processed(
                        email,
                        message_id,
                        history_id=notified_history_id,
                    )

        # Aggiorna lastHistoryIdProcessed
        self._update_last_history_id(email, notified_history_id)

        logger.info(
            f"[WATCH] ✅ Processamento completato per {email}: "
            f"{processed_count} processate, {skipped_count} saltate"
        )

    def _is_email_relevant(self, parsed: ParsedEmail, pms_provider: str | None) -> bool:
        """
        Verifica se un'email è rilevante in base al pmsProvider.
        
        Regole:
        - Email messaggi guest (Booking/Airbnb): sempre processate (non dipendono da pmsProvider)
        - Email conferme prenotazioni Scidoo: solo se pmsProvider == "scidoo"
        - Altre email: non processate
        """
        kind = parsed.kind

        # Email messaggi guest: sempre rilevanti (non dipendono da pmsProvider)
        if kind in ["booking_message", "airbnb_message"]:
            return True

        # Email conferme/cancellazioni prenotazioni Scidoo: solo se pmsProvider == "scidoo"
        if kind in ["scidoo_confirmation", "scidoo_cancellation"]:
            if pms_provider == "scidoo":
                return True
            else:
                logger.debug(f"[WATCH] Email Scidoo ignorata: pmsProvider={pms_provider} != 'scidoo'")
                return False

        # Email conferme/cancellazioni Booking/Airbnb: sempre rilevanti (non dipendono da pmsProvider)
        if kind in ["booking_confirmation", "airbnb_confirmation", "airbnb_cancellation"]:
            return True

        # Email non gestite: non processate
        if kind == "unhandled":
            return False

        # Default: non processare
        return False

    def _get_pms_provider_from_host(self, host_id: str) -> str | None:
        """Recupera pmsProvider dalla collezione hosts."""
        try:
            host_doc = self._firestore_client.collection("hosts").document(host_id).get()
            if host_doc.exists:
                data = host_doc.to_dict()
                return data.get("pmsProvider")
        except Exception as e:
            logger.warning(f"[WATCH] Errore recupero pmsProvider per host {host_id}: {e}")
        return None

    def _update_last_history_id(self, email: str, history_id: str) -> None:
        """Aggiorna lastHistoryIdProcessed in Firestore."""
        try:
            doc_ref = self._integration_repository._collection.document(email)
            doc_ref.update({"lastHistoryIdProcessed": history_id})
        except Exception as e:
            logger.error(f"[WATCH] Errore aggiornamento lastHistoryId per {email}: {e}")

    def _update_integration_status(self, email: str, status: str) -> None:
        """Aggiorna status integrazione in Firestore."""
        try:
            doc_ref = self._integration_repository._collection.document(email)
            doc_ref.update({"status": status})
        except Exception as e:
            logger.error(f"[WATCH] Errore aggiornamento status per {email}: {e}")

    def _save_ai_response(
        self,
        context: GuestMessageContext,
        guest_message: str,
        ai_reply: str,
        gmail_message_id: str,
        reply_message_id: Optional[str],
    ) -> None:
        """
        Salva la risposta AI in Firestore.
        
        La risposta è salvata in: properties/{propertyId}/conversations/{clientId}/messages
        """
        try:
            messages_ref = (
                self._firestore_client
                .collection("properties")
                .document(context.property_id)
                .collection("conversations")
                .document(context.client_id)
                .collection("messages")
            )

            # Salva la risposta AI
            message_data = {
                "sender": "host_ai",
                "text": ai_reply,
                "timestamp": firestore.SERVER_TIMESTAMP,
                "source": "ai_reply",
                "gmailMessageId": gmail_message_id,
                "replyMessageId": reply_message_id,
                "reservationId": context.reservation_id,
                "guestMessage": guest_message,  # Salva anche il messaggio originale per contesto
            }

            messages_ref.add(message_data)
            logger.info(f"[WATCH] Risposta AI salvata in conversazione: property={context.property_id}, client={context.client_id}")
        except Exception as e:
            logger.error(f"[WATCH] Errore salvataggio risposta AI: {e}", exc_info=True)

