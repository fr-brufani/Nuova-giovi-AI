from __future__ import annotations

import base64
import logging
import time
from typing import Optional

import requests

from ..config.settings import get_settings
from ..services.guest_message_pipeline import GuestMessageContext

logger = logging.getLogger(__name__)


class GeminiService:
    """Service per chiamare Gemini API e generare risposte AI."""

    def __init__(self):
        self._settings = get_settings()
        self._api_key = self._settings.gemini_api_key
        self._api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

    def generate_reply(
        self,
        context: GuestMessageContext,
        guest_message: str,
        max_retries: int = 3,
        initial_retry_delay: float = 1.0,
        attachments: Optional[list[dict]] = None,
    ) -> Optional[str]:
        """
        Genera una risposta AI usando Gemini per un messaggio guest.
        
        Args:
            context: Contesto del messaggio (property, cliente, prenotazione, conversazione)
            guest_message: Testo del messaggio dell'ospite
            max_retries: Numero massimo di tentativi in caso di errori temporanei
            initial_retry_delay: Delay iniziale in secondi per il retry (backoff esponenziale)
            attachments: Lista allegati [{"url": str, "fileName": str, "fileType": str}]
        
        Returns:
            Risposta generata da Gemini, o None in caso di errore
        """
        if not self._api_key:
            logger.error("[GEMINI] API key non configurata")
            return None

        prompt = self._build_prompt(context, guest_message, attachments)
        
        # Costruisci parts con testo e immagini
        parts = [{"text": prompt}]
        
        # Aggiungi immagini se presenti
        if attachments:
            image_parts = self._process_image_attachments(attachments)
            parts.extend(image_parts)
        
        request_data = {
            "contents": [
                {
                    "role": "user",
                    "parts": parts,
                }
            ],
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE",
                },
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE",
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE",
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE",
                },
            ],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 1024,
            },
        }

        # Retry loop per errori temporanei
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self._api_url,
                    params={"key": self._api_key},
                    json=request_data,
                    timeout=30,
                )

                response.raise_for_status()
                result = response.json()

                # Estrai testo dalla risposta
                candidates = result.get("candidates", [])
                if not candidates:
                    logger.warning("[GEMINI] Nessuna risposta generata. Response: %s", result)
                    return None

                candidate = candidates[0]
                
                # Verifica se la risposta è stata bloccata
                finish_reason = candidate.get("finishReason")
                if finish_reason and finish_reason != "STOP":
                    logger.warning(
                        f"[GEMINI] Risposta bloccata. finishReason={finish_reason}, "
                        f"safetyRatings={candidate.get('safetyRatings', [])}"
                    )
                    return None

                # Verifica safety ratings
                safety_ratings = candidate.get("safetyRatings", [])
                blocked_ratings = [r for r in safety_ratings if r.get("blocked", False)]
                if blocked_ratings:
                    logger.warning(
                        f"[GEMINI] Risposta bloccata da safety settings: {blocked_ratings}"
                    )
                    return None

                content = candidate.get("content", {})
                parts = content.get("parts", [])
                if not parts:
                    logger.warning(
                        f"[GEMINI] Risposta senza parti. Candidate: {candidate}, "
                        f"finishReason={finish_reason}"
                    )
                    return None

                text = parts[0].get("text", "").strip()
                if not text:
                    logger.warning("[GEMINI] Risposta vuota")
                    return None

                logger.info(f"[GEMINI] ✅ Risposta generata ({len(text)} caratteri)")
                return text

            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response else None
                
                # Retry solo per errori temporanei del server (5xx)
                if status_code and status_code >= 500 and status_code < 600 and attempt < max_retries - 1:
                    retry_delay = initial_retry_delay * (2 ** attempt)  # Backoff esponenziale
                    logger.warning(
                        f"[GEMINI] Errore {status_code} (tentativo {attempt + 1}/{max_retries}). "
                        f"Riprovo tra {retry_delay:.1f} secondi... Errore: {e}"
                    )
                    time.sleep(retry_delay)
                    continue
                else:
                    # Errore non recuperabile o ultimo tentativo
                    logger.error(
                        f"[GEMINI] Errore HTTP {status_code} chiamata API: {e}", 
                        exc_info=True
                    )
                    return None
                    
            except requests.exceptions.RequestException as e:
                # Errori di rete/connessione - ritenta solo se non è l'ultimo tentativo
                if attempt < max_retries - 1:
                    retry_delay = initial_retry_delay * (2 ** attempt)
                    logger.warning(
                        f"[GEMINI] Errore connessione (tentativo {attempt + 1}/{max_retries}). "
                        f"Riprovo tra {retry_delay:.1f} secondi... Errore: {e}"
                    )
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"[GEMINI] Errore chiamata API: {e}", exc_info=True)
                    return None
                    
            except Exception as e:
                # Errori non recuperabili - non ritentare
                logger.error(f"[GEMINI] Errore generazione risposta: {e}", exc_info=True)
                return None

        # Se arriviamo qui, abbiamo esaurito tutti i tentativi
        logger.error(
            f"[GEMINI] ❌ Impossibile generare risposta dopo {max_retries} tentativi"
        )
        return None

    def _build_prompt(
        self,
        context: GuestMessageContext,
        guest_message: str,
        attachments: Optional[list[dict]] = None,
    ) -> str:
        """
        Costruisce il prompt per Gemini con tutto il contesto necessario.
        """
        # Costruisci contesto property con tutti i dettagli disponibili
        property_data = context.property_data or {}
        property_context = f"Alloggio: {context.property_name or 'N/A'}\n"
        
        # Aggiungi indirizzo
        if property_data.get("address"):
            property_context += f"Indirizzo: {property_data['address']}\n"
        if property_data.get("city"):
            property_context += f"Città: {property_data['city']}\n"
        if property_data.get("country"):
            property_context += f"Paese: {property_data['country']}\n"
        
        # Aggiungi codice accesso e istruzioni
        if property_data.get("accessCode"):
            property_context += f"Codice di accesso: {property_data['accessCode']}\n"
        if property_data.get("accessInstructions"):
            property_context += f"Istruzioni per l'accesso: {property_data['accessInstructions']}\n"
        
        # Aggiungi istruzioni generali
        if property_data.get("instructions"):
            property_context += f"Istruzioni generali: {property_data['instructions']}\n"
        
        # Aggiungi istruzioni per lasciare i bagagli
        if property_data.get("luggageDropOffInstructions"):
            property_context += f"Dove lasciare i bagagli: {property_data['luggageDropOffInstructions']}\n"
        
        # Aggiungi info su parcheggio (cerca in varie varianti del campo)
        parking_info = (
            property_data.get("parking") or 
            property_data.get("parkingInfo") or 
            property_data.get("parkingInstructions")
        )
        if parking_info:
            property_context += f"Informazioni parcheggio: {parking_info}\n"
        
        # Aggiungi orari check-in/check-out
        if property_data.get("checkInTime"):
            property_context += f"Orario check-in: {property_data['checkInTime']}\n"
        if property_data.get("checkOutTime"):
            property_context += f"Orario check-out: {property_data['checkOutTime']}\n"
        
        # Aggiungi capacità
        if property_data.get("capacity"):
            property_context += f"Capacità: {property_data['capacity']} ospiti\n"
        
        # Aggiungi note interne (potrebbero contenere info utili)
        if property_data.get("interiorNotes"):
            property_context += f"Note interne: {property_data['interiorNotes']}\n"
        
        property_context += "\n"
        
        # Costruisci contesto prenotazione
        reservation_context = f"Prenotazione ID: {context.reservation_id}\n"
        
        # Costruisci contesto cliente
        client_context = f"Ospite: {context.client_name or 'N/A'}\n"
        if context.client_email:
            client_context += f"Email: {context.client_email}\n"

        # Costruisci storia conversazione
        conversation_history = ""
        if context.conversation_history:
            conversation_history = "\n--- STORIA CONVERSAZIONE PRECEDENTE ---\n"
            for msg in context.conversation_history[-5:]:  # Ultimi 5 messaggi
                sender = msg.get("sender", "unknown")
                text = msg.get("text", "")
                conversation_history += f"{sender.upper()}: {text}\n"
            conversation_history += "--- FINE STORIA ---\n"

        # Aggiungi info su allegati se presenti
        attachments_context = ""
        if attachments:
            image_urls = []
            for att in attachments:
                file_type = att.get("fileType", "").lower()
                if file_type.startswith("image/"):
                    url = att.get("url", "")
                    if url:
                        image_urls.append(url)
            
            if image_urls:
                attachments_context = "\n--- ALLEGATI IMMAGINI ---\n"
                for idx, img_url in enumerate(image_urls, 1):
                    attachments_context += f"Immagine {idx}: {img_url}\n"
                attachments_context += "--- FINE ALLEGATI ---\n"
                attachments_context += "\nL'ospite ha allegato delle immagini. Se sono rilevanti per la domanda, considera anche il contenuto delle immagini nella tua risposta.\n"

        # Prompt principale
        prompt = f"""Sei "Giovi AI", un assistente concierge virtuale amichevole, preciso e disponibile per l'alloggio chiamato "{context.property_name or 'questo alloggio'}".

Il tuo compito è:
- Se la domanda è informativa e l'informazione è presente nel contesto fornito, rispondi in modo completo.
- Se l'informazione richiesta NON è presente o è incompleta: Rispondi: "Mi dispiace, non ho questa informazione specifica nei dettagli forniti dall'host." NON inventare dettagli.
- Se la domanda è ambigua, chiedi gentilmente di specificare meglio.
- Se hai già risposto a domande simili nelle conversazioni precedenti, puoi fare riferimento a quelle risposte per mantenere coerenza.

Rispondi in modo cortese e con frasi complete.

--- CONTESTO ---
{property_context}{reservation_context}{client_context}{conversation_history}{attachments_context}

--- MESSAGGIO OSPITE ---
"{guest_message}"

--- RISPOSTA ---
"""

        return prompt
    
    def _process_image_attachments(self, attachments: list[dict]) -> list[dict]:
        """
        Scarica e converte le immagini dagli attachments in formato base64 per Gemini.
        
        Args:
            attachments: Lista di attachments [{"url": str, "fileName": str, "fileType": str}]
            
        Returns:
            Lista di parts per Gemini con inline_data
        """
        image_parts = []
        
        for att in attachments:
            file_type = att.get("fileType", "").lower()
            url = att.get("url", "")
            
            # Solo immagini
            if not file_type.startswith("image/"):
                continue
            
            if not url:
                logger.warning(f"[GEMINI] URL immagine vuota per attachment: {att}")
                continue
            
            try:
                # Scarica immagine
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                image_data = response.content
                if not image_data:
                    logger.warning(f"[GEMINI] Immagine vuota da URL: {url}")
                    continue
                
                # Converti in base64
                base64_data = base64.b64encode(image_data).decode('utf-8')
                
                # Determina mime_type (default per compatibilità)
                mime_type = file_type
                if not mime_type or mime_type == "application/octet-stream":
                    # Prova a dedurre dal nome file o usa jpeg come default
                    if url.endswith(('.png', '.PNG')):
                        mime_type = "image/png"
                    elif url.endswith(('.gif', '.GIF')):
                        mime_type = "image/gif"
                    elif url.endswith(('.webp', '.WEBP')):
                        mime_type = "image/webp"
                    else:
                        mime_type = "image/jpeg"  # Default
                
                # Aggiungi come inline_data per Gemini
                image_parts.append({
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": base64_data,
                    }
                })
                
                logger.info(
                    f"[GEMINI] Immagine processata: {url}, tipo: {mime_type}, "
                    f"dimensione: {len(image_data)} bytes"
                )
                
            except requests.exceptions.RequestException as e:
                logger.error(f"[GEMINI] Errore download immagine da {url}: {e}", exc_info=True)
                continue
            except Exception as e:
                logger.error(f"[GEMINI] Errore processamento immagine da {url}: {e}", exc_info=True)
                continue
        
        return image_parts

