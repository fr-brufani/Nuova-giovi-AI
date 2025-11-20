# 🏢 Gestione Multi-Host - Booking.com Integration

**Importante:** Il servizio Booking.com gestisce **TUTTI gli host contemporaneamente** usando credenziali condivise.

---

## 🔑 Architettura Multi-Host

### **Credenziali Condivise**
- **Una sola Machine Account Booking.com** per provider
- Credenziali condivise tra tutti gli host
- API restituisce prenotazioni/messaggi per **TUTTE le properties** del provider

### **Mappatura Necessaria**
- **Problema:** L'API Booking.com non indica direttamente quale host possiede una property
- **Soluzione:** Tabella mapping `bookingPropertyMappings` in Firestore

```
booking_property_id (Booking.com) → host_id (nostro sistema)
```

---

## 📊 Struttura Mapping

### **Firestore Collection: `bookingPropertyMappings`**

```javascript
{
  id: "mapping-123",
  bookingPropertyId: "8011855",        // Property ID Booking.com
  hostId: "host-abc-123",              // ID host proprietario
  internalPropertyId: "property-xyz",  // Property ID interno (opzionale)
  propertyName: "Villa Bella Vista",   // Nome property (opzionale)
  createdAt: Timestamp,
  updatedAt: Timestamp
}
```

### **Repository**
- `BookingPropertyMappingsRepository` - Gestione CRUD mapping
- `get_by_booking_property_id()` - Trova host_id per property_id Booking.com
- `get_by_host()` - Lista tutte le properties di un host

---

## 🔄 Flusso Multi-Host

### **Flow: Import Prenotazioni**

```
1. BookingReservationPollingService.poll_new_reservations()
   └─> GET /OTA_HotelResNotif
   └─> Ritorna XML con prenotazioni per TUTTE le properties

2. Per ogni prenotazione nell'XML:
   ├─> parse_ota_xml() → BookingReservation
   ├─> _find_host_id_for_property(booking_property_id)
   │   └─> BookingPropertyMappingsRepository.get_by_booking_property_id()
   │   └─> Ritorna host_id o None
   │
   ├─> Se host_id trovato:
   │   └─> PersistenceService.save_booking_reservation(reservation, host_id)
   │       └─> Salva con host_id corretto
   │
   └─> Se host_id NON trovato:
       └─> Log warning, salta prenotazione (non fa acknowledgement)

3. Acknowledgement per tutte le prenotazioni processate
   └─> POST /OTA_HotelResNotif
```

### **Flow: Messaggi**

```
1. BookingMessagePollingService.poll_messages()
   └─> GET /messages/latest
   └─> Ritorna messaggi per TUTTE le properties

2. Per ogni messaggio:
   ├─> Estrai reservation_id da conversation_reference
   ├─> Trova reservation in Firestore per reservation_id
   ├─> Estrai property_id dalla reservation
   ├─> Trova host_id usando mapping booking_property_id → host_id
   ├─> Processa messaggio con host_id corretto
   └─> Invia risposta come host corretto
```

---

## ⚠️ Gestione Prenotazioni senza Mapping

### **Cosa succede se non c'è mapping:**

1. **Prenotazione senza mapping:**
   - Log warning: `⚠️ Nessun mapping trovato per booking_property_id=8011855`
   - Prenotazione **NON viene salvata**
   - Prenotazione **NON viene fatta acknowledgement**
   - Prenotazione rimane nella coda Booking.com
   - Dopo 30 minuti, Booking.com invia **fallback email** al property

2. **Come risolvere:**
   - Creare mapping manualmente in Firestore:
     ```javascript
     bookingPropertyMappings/{new-id} = {
       bookingPropertyId: "8011855",
       hostId: "host-abc-123",
       createdAt: Timestamp.now()
     }
     ```
   - Oppure: API endpoint per creare mapping (da implementare)

---

## 🔧 Implementazione

### **1. Repository Mapping** ✅ FATTO
- `repositories/booking_property_mappings.py`
- CRUD completo per mapping

### **2. Polling Service Multi-Host** ✅ AGGIORNATO
- `services/booking_reservation_polling_service.py`
- Gestisce TUTTI gli host
- Mappa ogni prenotazione al corretto host_id

### **3. Persistence Service** ⏳ DA ESTENDERE
- `services/persistence_service.py`
- Metodo `save_booking_reservation(reservation, host_id)`
- Salva con host_id corretto (già determinato dal polling)

### **4. API Endpoint Mapping** ⏳ DA CREARE
- `api/routes/booking_property_mappings.py`
- GET/POST/PATCH/DELETE per gestire mapping
- Lista mapping per host

---

## 📋 Task Multi-Host da Completare

### **Fase 2A: Import Prenotazioni**

- [x] **T2A.6.1** Repository mapping `bookingPropertyMappings` ✅
- [x] **T2A.3.1** Polling service multi-host ✅
- [ ] **T2A.6.2** API endpoint per gestire mapping
  - GET `/hosts/{host_id}/booking-property-mappings`
  - POST `/hosts/{host_id}/booking-property-mappings`
  - PATCH `/hosts/{host_id}/booking-property-mappings/{mapping_id}`
  - DELETE `/hosts/{host_id}/booking-property-mappings/{mapping_id}`
- [ ] **T2A.5.1** Estendere `PersistenceService.save_booking_reservation()`
  - Supporta BookingReservation
  - Usa host_id già determinato
  - Crea/aggiorna property e client

### **Fase 2B: Messaging**

- [ ] **T2B.1.1** Message polling service multi-host
  - Mappa messaggi al corretto host_id
  - Usa reservation_id → property_id → mapping → host_id

### **Fase 3: Testing Multi-Host**

- [ ] **T3.1.1** Test con 2+ host contemporaneamente
- [ ] **T3.1.2** Verifica mapping corretto
- [ ] **T3.1.3** Test prenotazioni senza mapping (devono essere saltate)

---

## 💡 Raccomandazioni

### **Setup Iniziale Mapping**

1. **Quando un host configura Booking.com:**
   - L'host deve fornire lista `booking_property_id` delle sue properties
   - Creare mapping per ogni property
   - Può essere fatto via API endpoint o manualmente in Firestore

2. **Mapping Automatico (Future Enhancement):**
   - Quando una prenotazione arriva senza mapping
   - Creare property automatica con `requiresReview=True`
   - Richiedere all'host di confermare mapping via UI

3. **Fallback Email:**
   - Se mapping non esiste, Booking.com invia email fallback
   - Il sistema email esistente può parsare email e creare prenotazione
   - Poi l'host può creare mapping per evitare duplicati

---

## 🚨 Errori Comuni

### **Prenotazione saltata senza motivo:**
- **Causa:** Manca mapping `booking_property_id` → `host_id`
- **Fix:** Creare mapping in Firestore o via API

### **Prenotazione salvata con host_id sbagliato:**
- **Causa:** Mapping errato in Firestore
- **Fix:** Aggiornare mapping con host_id corretto

### **Prenotazione duplicata:**
- **Causa:** Mapping creato dopo che prenotazione è già arrivata via email fallback
- **Fix:** Deduplicazione per `reservation_id` in `PersistenceService`

---

## ✅ Checklist Setup Multi-Host

- [ ] Credenziali Machine Account Booking.com (condivise)
- [ ] Mapping iniziale per tutte le properties attive
- [ ] Polling service avviato (gestisce tutti gli host)
- [ ] API endpoint per gestire mapping (creare/aggiornare)
- [ ] Test con 2+ host contemporaneamente
- [ ] Documentazione per setup mapping nuovi host

---

**Ricorda:** Il servizio è **multi-host by design**. Ogni prenotazione/messaggio viene automaticamente mappato al corretto host usando `booking_property_id` → `host_id` mapping.

