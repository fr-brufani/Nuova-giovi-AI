#!/usr/bin/env python3
"""Script per verificare i risultati del matching delle property."""

import json
import sys
from pathlib import Path

# Aggiungi src al path per importare i moduli
sys.path.insert(0, str(Path(__file__).parent / "src"))

from email_agent_service.dependencies.firebase import get_firestore_client

# Host ID da verificare - se non specificato, analizza tutti gli host
HOST_ID = "YMweo32F7lexdEPkJE8PjoPtOKD2"  # Cambia questo se necessario
ANALYZE_ALL = False  # Se True, analizza tutti gli host invece di uno specifico


def serialize_timestamp(ts):
    """Converte un timestamp Firestore in stringa."""
    if hasattr(ts, "timestamp"):
        return ts.timestamp()
    if hasattr(ts, "isoformat"):
        return ts.isoformat()
    return str(ts)


def serialize_doc(doc):
    """Serializza un documento Firestore."""
    data = doc.to_dict()
    if data is None:
        return None
    
    # Converti i timestamp
    for key, value in data.items():
        if hasattr(value, "timestamp") or hasattr(value, "isoformat"):
            data[key] = serialize_timestamp(value)
    
    return {"id": doc.id, **data}


def analyze_database():
    """Analizza il database e verifica i risultati del matching."""
    print("🔍 Connessione a Firestore...")
    client = get_firestore_client()
    
    print(f"📊 Analisi dati per host: {HOST_ID}\n")
    
    # Prima verifica se ci sono property nel database
    properties_ref = client.collection("properties")
    
    # Cerca tutte le property per vedere quali hostId esistono
    print("🔍 Cercando tutti gli host nel database...")
    all_properties = list(properties_ref.stream())
    
    if not all_properties:
        print("❌ Nessuna property trovata nel database!")
        return False
    
    print(f"📊 Trovate {len(all_properties)} property totali nel database")
    
    # Estrai tutti gli hostId unici
    host_ids = set()
    for doc in all_properties:
        data = doc.to_dict()
        if data:
            host_id = data.get("hostId")
            if host_id:
                host_ids.add(host_id)
    
    if not host_ids:
        print("❌ Nessun hostId trovato nelle property!")
        return False
    
    print(f"\n📋 Host ID trovati: {', '.join(sorted(host_ids))}")
    
    # Determina quale hostId usare
    if ANALYZE_ALL:
        actual_host_id = None
        print("\n🔍 Analizzando TUTTI gli host")
    elif HOST_ID in host_ids:
        actual_host_id = HOST_ID
        print(f"\n🔍 Analizzando host specifico: {HOST_ID}")
    else:
        # Usa il primo hostId trovato se quello specificato non esiste
        actual_host_id = list(host_ids)[0]
        print(f"\n⚠️  Host ID '{HOST_ID}' non trovato nei dati.")
        print(f"⚠️  Userò il primo hostId disponibile: '{actual_host_id}'")
    
    # 1. Analizza properties
    print("\n" + "=" * 60)
    print("1. PROPERTIES")
    print("=" * 60)
    
    if actual_host_id:
        properties_query = properties_ref.where("hostId", "==", actual_host_id)
        print(f"🔍 Analizzando host: {actual_host_id}")
    else:
        properties_query = properties_ref
        print("🔍 Analizzando tutti gli host")
    
    properties_docs = list(properties_query.stream())
    
    managed_properties = []
    imported_properties = []
    
    for doc in properties_docs:
        data = serialize_doc(doc)
        if data:
            imported_from = data.get("importedFrom")
            requires_review = data.get("requiresReview", False)
            
            if imported_from == "airbnb_email" or requires_review:
                imported_properties.append(data)
            else:
                managed_properties.append(data)
    
    print(f"\n✅ Property gestite: {len(managed_properties)}")
    for prop in managed_properties:
        print(f"   - {prop.get('name', 'N/A')} (ID: {prop['id']})")
    
    print(f"\n⚠️  Property importate (dovrebbero essere 0): {len(imported_properties)}")
    for prop in imported_properties:
        print(f"   - {prop.get('name', 'N/A')} (ID: {prop['id']}, importedFrom: {prop.get('importedFrom')}, requiresReview: {prop.get('requiresReview')})")
    
    managed_property_ids = {p["id"] for p in managed_properties}
    
    # 2. Analizza reservations
    print("\n" + "=" * 60)
    print("2. RESERVATIONS")
    print("=" * 60)
    
    reservations_ref = client.collection("reservations")
    if actual_host_id:
        reservations_query = reservations_ref.where("hostId", "==", actual_host_id)
    else:
        reservations_query = reservations_ref
    reservations_docs = list(reservations_query.stream())
    
    print(f"\n📋 Totale prenotazioni: {len(reservations_docs)}")
    
    valid_reservations = []
    invalid_reservations = []
    
    for doc in reservations_docs:
        data = serialize_doc(doc)
        if data:
            property_id = data.get("propertyId")
            if property_id and property_id in managed_property_ids:
                valid_reservations.append(data)
            else:
                invalid_reservations.append(data)
    
    print(f"✅ Prenotazioni con propertyId valido: {len(valid_reservations)}")
    print(f"❌ Prenotazioni con propertyId NON valido o mancante: {len(invalid_reservations)}")
    
    if invalid_reservations:
        print("\n⚠️  Prenotazioni problematiche:")
        for res in invalid_reservations[:10]:  # Mostra max 10
            print(f"   - Reservation ID: {res['id']}")
            print(f"     Property ID: {res.get('propertyId', 'MANCANTE')}")
            print(f"     Property Name: {res.get('propertyName', 'N/A')}")
            print(f"     Guest: {res.get('guestName', 'N/A')}")
            print()
    
    # 3. Analizza clients
    print("\n" + "=" * 60)
    print("3. CLIENTS")
    print("=" * 60)
    
    clients_ref = client.collection("clients")
    # I clients potrebbero non avere hostId direttamente, cercare per assignedHostId
    if actual_host_id:
        clients_query = clients_ref.where("assignedHostId", "==", actual_host_id)
    else:
        clients_query = clients_ref
    clients_docs = list(clients_query.stream())
    
    print(f"\n👥 Totale clienti: {len(clients_docs)}")
    
    clients_with_property = []
    clients_without_property = []
    clients_with_invalid_property = []
    
    for doc in clients_docs:
        data = serialize_doc(doc)
        if data:
            property_id = data.get("assignedPropertyId")
            if not property_id:
                clients_without_property.append(data)
            elif property_id in managed_property_ids:
                clients_with_property.append(data)
            else:
                clients_with_invalid_property.append(data)
    
    print(f"✅ Clienti con assignedPropertyId valido: {len(clients_with_property)}")
    print(f"⚠️  Clienti senza assignedPropertyId: {len(clients_without_property)}")
    print(f"❌ Clienti con assignedPropertyId NON valido: {len(clients_with_invalid_property)}")
    
    if clients_with_invalid_property:
        print("\n⚠️  Clienti problematici:")
        for client in clients_with_invalid_property[:10]:  # Mostra max 10
            print(f"   - Client ID: {client['id']}")
            print(f"     Name: {client.get('name', 'N/A')}")
            print(f"     Property ID: {client.get('assignedPropertyId', 'MANCANTE')}")
            print()
    
    # 4. Riepilogo finale
    print("\n" + "=" * 60)
    print("4. RIEPILOGO FINALE")
    print("=" * 60)
    
    all_valid = (
        len(imported_properties) == 0
        and len(invalid_reservations) == 0
        and len(clients_with_invalid_property) == 0
    )
    
    print(f"\n{'✅' if all_valid else '❌'} Verifica completata!")
    print(f"\n📊 Statistiche:")
    print(f"   - Property gestite: {len(managed_properties)}")
    print(f"   - Property importate rimanenti: {len(imported_properties)}")
    print(f"   - Prenotazioni totali: {len(reservations_docs)}")
    print(f"   - Prenotazioni valide: {len(valid_reservations)}")
    print(f"   - Prenotazioni problematiche: {len(invalid_reservations)}")
    print(f"   - Clienti totali: {len(clients_docs)}")
    print(f"   - Clienti con property valida: {len(clients_with_property)}")
    print(f"   - Clienti problematici: {len(clients_with_invalid_property)}")
    
    if all_valid:
        print("\n✅ ✅ ✅ IL MATCHING HA FUNZIONATO CORRETTAMENTE! ✅ ✅ ✅")
        print("   - Tutte le property importate sono state eliminate")
        print("   - Tutte le prenotazioni sono associate a property gestite")
        print("   - Tutti i clienti sono associati a property gestite")
    else:
        print("\n⚠️  ⚠️  ⚠️  CI SONO PROBLEMI DA RISOLVERE ⚠️  ⚠️  ⚠️")
        if len(imported_properties) > 0:
            print(f"   - Ci sono ancora {len(imported_properties)} property importate nel database")
        if len(invalid_reservations) > 0:
            print(f"   - Ci sono {len(invalid_reservations)} prenotazioni con propertyId non valido")
        if len(clients_with_invalid_property) > 0:
            print(f"   - Ci sono {len(clients_with_invalid_property)} clienti con assignedPropertyId non valido")
    
    # 5. Esporta dati completi in JSON
    output_file = Path(__file__).parent / "matching_verification_results.json"
    results = {
        "hostId": actual_host_id if actual_host_id else "ALL",
        "requestedHostId": HOST_ID,
        "properties": {
            "managed": managed_properties,
            "imported": imported_properties,
            "total": len(properties_docs),
        },
        "reservations": {
            "total": len(reservations_docs),
            "valid": valid_reservations,
            "invalid": invalid_reservations,
        },
        "clients": {
            "total": len(clients_docs),
            "with_valid_property": clients_with_property,
            "without_property": clients_without_property,
            "with_invalid_property": clients_with_invalid_property,
        },
        "verification": {
            "all_valid": all_valid,
            "imported_properties_count": len(imported_properties),
            "invalid_reservations_count": len(invalid_reservations),
            "invalid_clients_count": len(clients_with_invalid_property),
        },
    }
    
    output_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n💾 Dati completi esportati in: {output_file}")
    
    return all_valid


if __name__ == "__main__":
    try:
        success = analyze_database()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Errore durante l'analisi: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

