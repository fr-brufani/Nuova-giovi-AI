"""Repository per gestire integrazioni Scidoo (API keys)."""

from __future__ import annotations

from typing import Optional

from firebase_admin import firestore


class ScidooIntegrationsRepository:
    """Repository per gestire credenziali API Scidoo salvate in hosts collection."""
    
    HOSTS_COLLECTION = "hosts"
    
    def __init__(self, client: firestore.Client):
        self._client = client
    
    def get_api_key(self, host_id: str) -> Optional[str]:
        """
        Recupera API key Scidoo per un host.
        
        Args:
            host_id: ID host
            
        Returns:
            API key se presente, None altrimenti
        """
        doc = self._client.collection(self.HOSTS_COLLECTION).document(host_id).get()
        if not doc.exists:
            return None
        
        data = doc.to_dict() or {}
        return data.get("scidooApiKey")
    
    def save_api_key(self, host_id: str, api_key: str) -> None:
        """
        Salva API key Scidoo per un host.
        
        Args:
            host_id: ID host
            api_key: API key Scidoo
        """
        doc_ref = self._client.collection(self.HOSTS_COLLECTION).document(host_id)
        doc_ref.set(
            {
                "scidooApiKey": api_key,
                "scidooConfiguredAt": firestore.SERVER_TIMESTAMP,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )
    
    def has_integration(self, host_id: str) -> bool:
        """
        Verifica se un host ha integrazione Scidoo configurata.
        
        Args:
            host_id: ID host
            
        Returns:
            True se ha API key configurata
        """
        return self.get_api_key(host_id) is not None
    
    def get_all_hosts_with_integration(self) -> list[tuple[str, str]]:
        """
        Recupera tutti gli host con integrazione Scidoo configurata.
        
        Returns:
            Lista di tuple (host_id, api_key)
        """
        query = self._client.collection(self.HOSTS_COLLECTION)
        docs = list(query.get())
        
        hosts = []
        for doc in docs:
            data = doc.to_dict() or {}
            api_key = data.get("scidooApiKey")
            if api_key:
                hosts.append((doc.id, api_key))
        
        return hosts
    
    def remove_integration(self, host_id: str) -> None:
        """
        Rimuove integrazione Scidoo per un host.
        
        Args:
            host_id: ID host
        """
        doc_ref = self._client.collection(self.HOSTS_COLLECTION).document(host_id)
        doc_ref.update({
            "scidooApiKey": firestore.DELETE_FIELD,
            "scidooConfiguredAt": firestore.DELETE_FIELD,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        })

