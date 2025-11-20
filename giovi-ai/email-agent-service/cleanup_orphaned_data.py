#!/usr/bin/env python3
"""Script per pulire prenotazioni e clienti orfani (con propertyId che non esiste più)."""

import sys
from pathlib import Path

# Aggiungi src al path per importare i moduli
sys.path.insert(0, str(Path(__file__).parent / "src"))

from email_agent_service.dependencies.firebase import get_firestore_client

HOST_ID = "YMweo32F7IexdEPkJE8PjoPtOKD2"  # Host ID da pulire


def cleanup_orphaned_data():
    """Pulisce prenotazioni e clienti con propertyId che non esiste più."""
    print("🔍 Connessione a Firestore...")
    client = get_firestore_client()
    
    print(f"🧹 Pulizia dati orfani per host: {HOST_ID}\n")
    
    # 1. Carica tutte le property gestite per ottenere gli ID validi
    properties_ref = client.collection("properties")
    properties_query = properties_ref.where("hostId", "==", HOST_ID)
    properties_docs = list(properties_query.stream())
    
    valid_property_ids = {doc.id for doc in properties_docs}
    print(f"✅ Property valide trovate: {len(valid_property_ids)}")
    for doc in properties_docs:
        data = doc.to_dict()
        print(f"   - {data.get('name', 'N/A')} (ID: {doc.id})")
    
    # 2. Trova prenotazioni con propertyId non valido
    print("\n" + "=" * 60)
    print("2. PRENOTAZIONI ORFANE")
    print("=" * 60)
    
    reservations_ref = client.collection("reservations")
    reservations_query = reservations_ref.where("hostId", "==", HOST_ID)
    reservations_docs = list(reservations_query.stream())
    
    orphaned_reservations = []
    for doc in reservations_docs:
        data = doc.to_dict()
        property_id = data.get("propertyId")
        if property_id and property_id not in valid_property_ids:
            orphaned_reservations.append((doc.id, property_id, data.get("propertyName")))
    
    print(f"\n📋 Prenotazioni totali: {len(reservations_docs)}")
    print(f"❌ Prenotazioni orfane trovate: {len(orphaned_reservations)}")
    
    if orphaned_reservations:
        print("\n⚠️  Prenotazioni da eliminare:")
        for res_id, prop_id, prop_name in orphaned_reservations:
            print(f"   - Reservation ID: {res_id}")
            print(f"     Property ID (non valido): {prop_id}")
            print(f"     Property Name: {prop_name or 'N/A'}")
    
    # 3. Trova clienti con assignedPropertyId non valido
    print("\n" + "=" * 60)
    print("3. CLIENTI ORFANI")
    print("=" * 60)
    
    clients_ref = client.collection("clients")
    clients_query = clients_ref.where("assignedHostId", "==", HOST_ID)
    clients_docs = list(clients_query.stream())
    
    orphaned_clients = []
    for doc in clients_docs:
        data = doc.to_dict()
        property_id = data.get("assignedPropertyId")
        if property_id and property_id not in valid_property_ids:
            orphaned_clients.append((doc.id, property_id, data.get("name")))
    
    print(f"\n👥 Clienti totali: {len(clients_docs)}")
    print(f"❌ Clienti orfani trovati: {len(orphaned_clients)}")
    
    if orphaned_clients:
        print("\n⚠️  Clienti da eliminare:")
        for client_id, prop_id, name in orphaned_clients:
            print(f"   - Client ID: {client_id}")
            print(f"     Name: {name or 'N/A'}")
            print(f"     Property ID (non valido): {prop_id}")
    
    # 4. Conferma e pulizia
    if not orphaned_reservations and not orphaned_clients:
        print("\n✅ Nessun dato orfano trovato! Il database è pulito.")
        return True
    
    print("\n" + "=" * 60)
    print("4. PULIZIA")
    print("=" * 60)
    
    print(f"\n⚠️  ATTENZIONE: Stai per eliminare:")
    print(f"   - {len(orphaned_reservations)} prenotazioni")
    print(f"   - {len(orphaned_clients)} clienti")
    print(f"\n❓ Vuoi procedere? (scrivi 'SI' per confermare): ", end="")
    
    confirmation = input().strip().upper()
    if confirmation != "SI":
        print("❌ Operazione annullata.")
        return False
    
    # Elimina prenotazioni orfane
    deleted_reservations = 0
    for res_id, _, _ in orphaned_reservations:
        reservations_ref.document(res_id).delete()
        deleted_reservations += 1
    
    # Elimina clienti orfani
    deleted_clients = 0
    for client_id, _, _ in orphaned_clients:
        clients_ref.document(client_id).delete()
        deleted_clients += 1
    
    print(f"\n✅ Pulizia completata!")
    print(f"   - Prenotazioni eliminate: {deleted_reservations}")
    print(f"   - Clienti eliminati: {deleted_clients}")
    
    return True


if __name__ == "__main__":
    try:
        success = cleanup_orphaned_data()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Errore durante la pulizia: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

