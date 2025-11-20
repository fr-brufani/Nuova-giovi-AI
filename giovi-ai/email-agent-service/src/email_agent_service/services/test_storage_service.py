from __future__ import annotations

import logging
from datetime import datetime
from io import BytesIO
from typing import Optional

import firebase_admin
from firebase_admin import firestore, storage

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class TestStorageService:
    """Service per gestire upload di immagini/allegati per test su Firebase Storage."""

    def __init__(self, firestore_client: firestore.Client):
        self._firestore_client = firestore_client
        # Firebase Storage bucket - usa il default per il progetto
        try:
            # Assicurati che Firebase Admin sia inizializzato
            app = firebase_admin.get_app() if firebase_admin._apps else None
            if app:
                # Ottieni il bucket usando il project_id dall'app
                project_id = app.project_id
                if project_id:
                    # Costruisci il nome del bucket: {project_id}.appspot.com
                    bucket_name = f"{project_id}.appspot.com"
                    self._bucket = storage.bucket(bucket_name, app=app)
                else:
                    # Fallback: prova il bucket di default
                    self._bucket = storage.bucket(app=app)
            else:
                logger.warning("[TEST_STORAGE] Firebase Admin non inizializzato")
                self._bucket = None
        except Exception as e:
            logger.error(f"[TEST_STORAGE] Bucket Firebase Storage non disponibile: {e}", exc_info=True)
            self._bucket = None

    def upload_test_attachment(
        self,
        file_content: bytes,
        file_name: str,
        file_type: str,
        conversation_id: str,  # property_id/client_id per identificare conversazione
    ) -> Optional[dict]:
        """
        Upload di un file/allegato su Firebase Storage.
        
        Args:
            file_content: Contenuto del file in bytes
            file_name: Nome del file
            file_type: Tipo MIME (es. "image/jpeg", "image/png")
            conversation_id: ID conversazione (usato per organizzare i file)
        
        Returns:
            dict con {url, fileName, fileType} o None in caso di errore
        """
        if not self._bucket:
            logger.error("[TEST_STORAGE] Firebase Storage bucket non disponibile")
            return None

        try:
            # Path nel bucket: test-attachments/{conversation_id}/{timestamp}-{filename}
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Sanitize filename
            safe_filename = file_name.replace(" ", "_").replace("/", "_")
            storage_path = f"test-attachments/{conversation_id}/{timestamp}-{safe_filename}"
            
            # Upload file
            blob = self._bucket.blob(storage_path)
            blob.content_type = file_type
            
            # Imposta metadati per rendere il file pubblico leggibile
            blob.metadata = {
                "uploadedAt": timestamp,
                "conversationId": conversation_id,
                "isTest": "true",
            }
            
            # Upload
            blob.upload_from_string(file_content, content_type=file_type)
            
            # Rendi pubblico (per permettere a Gemini di accedere alle immagini)
            blob.make_public()
            
            # Ottieni URL pubblico
            public_url = blob.public_url
            
            logger.info(
                f"[TEST_STORAGE] File uploadato: {storage_path}, "
                f"size={len(file_content)} bytes, url={public_url}"
            )
            
            return {
                "url": public_url,
                "fileName": file_name,
                "fileType": file_type,
            }
            
        except Exception as e:
            logger.error(f"[TEST_STORAGE] Errore upload file: {e}", exc_info=True)
            return None

    def upload_from_base64(
        self,
        base64_content: str,
        file_name: str,
        file_type: str,
        conversation_id: str,
    ) -> Optional[dict]:
        """
        Upload da stringa base64 (utile per upload dal frontend).
        
        Args:
            base64_content: Contenuto base64 (può includere prefix data:image/...;base64,)
            file_name: Nome del file
            file_type: Tipo MIME
            conversation_id: ID conversazione
        
        Returns:
            dict con {url, fileName, fileType} o None
        """
        try:
            # Rimuovi prefix se presente
            if "," in base64_content:
                base64_content = base64_content.split(",", 1)[1]
            
            # Decodifica base64
            import base64
            file_content = base64.b64decode(base64_content)
            
            return self.upload_test_attachment(
                file_content=file_content,
                file_name=file_name,
                file_type=file_type,
                conversation_id=conversation_id,
            )
            
        except Exception as e:
            logger.error(f"[TEST_STORAGE] Errore upload da base64: {e}", exc_info=True)
            return None

