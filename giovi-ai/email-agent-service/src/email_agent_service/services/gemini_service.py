from __future__ import annotations

import logging
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
    ) -> Optional[str]:
        """
        Genera una risposta AI usando Gemini per un messaggio guest.
        
        Args:
            context: Contesto del messaggio (property, cliente, prenotazione, conversazione)
            guest_message: Testo del messaggio dell'ospite
        
        Returns:
            Risposta generata da Gemini, o None in caso di errore
        """
        if not self._api_key:
            logger.error("[GEMINI] API key non configurata")
            return None

        try:
            prompt = self._build_prompt(context, guest_message)
            
            response = requests.post(
                self._api_url,
                params={"key": self._api_key},
                json={
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": prompt}],
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
                },
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

        except requests.exceptions.RequestException as e:
            logger.error(f"[GEMINI] Errore chiamata API: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"[GEMINI] Errore generazione risposta: {e}", exc_info=True)
            return None

    def _build_prompt(
        self,
        context: GuestMessageContext,
        guest_message: str,
    ) -> str:
        """
        Costruisce il prompt per Gemini con tutto il contesto necessario.
        """
        # Costruisci contesto property
        property_context = f"Alloggio: {context.property_name or 'N/A'}\n"
        
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

        # Prompt principale
        prompt = f"""Sei "Giovi AI", un assistente concierge virtuale amichevole, preciso e disponibile per l'alloggio chiamato "{context.property_name or 'questo alloggio'}".

Il tuo compito è:
- Se la domanda è informativa e l'informazione è presente nel contesto fornito, rispondi in modo completo.
- Se l'informazione richiesta NON è presente o è incompleta: Rispondi: "Mi dispiace, non ho questa informazione specifica nei dettagli forniti dall'host." NON inventare dettagli.
- Se la domanda è ambigua, chiedi gentilmente di specificare meglio.
- Se hai già risposto a domande simili nelle conversazioni precedenti, puoi fare riferimento a quelle risposte per mantenere coerenza.

Rispondi in modo cortese e con frasi complete.

--- CONTESTO ---
{property_context}{reservation_context}{client_context}{conversation_history}

--- MESSAGGIO OSPITE ---
"{guest_message}"

--- RISPOSTA ---
"""

        return prompt

