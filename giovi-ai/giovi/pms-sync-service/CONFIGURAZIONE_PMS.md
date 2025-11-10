# 🏨 Documentazione Integrazioni PMS - giovi_ai

Questo documento descrive come funzionano le integrazioni PMS (Property Management System) implementate nel **pms-sync-service** di giovi_ai.

## 📋 **Panoramica Integrazioni Supportate**

| PMS | Stato | Tipo Integrazione | Funzionalità |
|-----|-------|------------------|--------------|
| **Smoobu** | ✅ **Completa** | API + Webhook | Configurazione automatica, Sync proprietà, Webhook real-time |
| **Scidoo** | ✅ **Completa** | API Pull | Sincronizzazione manuale, Import prenotazioni |
| **CSV Import** | ✅ **Disponibile** | File Upload | Import clienti e prenotazioni da CSV |

---

## 🚀 **INTEGRAZIONE SMOOBU** (Principale)

### **Caratteristiche Principali**

- ✅ **Configurazione Automatica** con solo API Key
- ✅ **Webhook Real-time** per prenotazioni
- ✅ **Sincronizzazione Proprietà** automatica
- ✅ **Gestione Completa Stati** prenotazioni
- ✅ **Auto-creazione Clienti** e Proprietà

### **🔧 Configurazione Iniziale**

#### **1. Prerequisiti**
- Account Smoobu attivo
- API Key Smoobu (dalla sezione Developer)
- Host registrato in giovi_ai con ruolo 'host'

#### **2. Configurazione Automatica**

**Endpoint:** `POST /config/smoobu`

```json
{
  "smoobuApiKey": "your-smoobu-api-key",
  "testConnection": true,
  "syncProperties": true
}
```

**Cosa fa automaticamente:**
1. 🔍 Testa la connessione API
2. 👤 Recupera User ID Smoobu
3. 🏠 Sincronizza tutte le proprietà
4. 💾 Salva configurazione nel database
5. 🔗 Fornisce URL webhook pronto

#### **3. Configurazione Webhook in Smoobu**

Dopo la configurazione automatica:
1. Copia l'URL webhook restituito (es. `https://your-domain.com/webhook/smoobu`)
2. Vai in **Smoobu > Impostazioni > Developer > Webhooks**
3. Incolla l'URL webhook
4. Abilita eventi: `newReservation`, `updateReservation`, `cancelReservation`
5. Salva le impostazioni

### **📡 Funzionamento Webhook Real-time**

#### **Endpoint Webhook:** `POST /webhook/smoobu`

**Payload Structure:**
```json
{
  "action": "newReservation|updateReservation|cancelReservation",
  "user": 123456,  // smoobuUserId
  "data": {
    "id": 12345,   // ID prenotazione Smoobu
    "reference-id": "BOOKING_REF_001",
    "arrival": "2024-03-15",
    "departure": "2024-03-18",
    "apartment": {
      "id": 101,
      "name": "Appartamento Roma Centro"
    },
    "guest-name": "Mario Rossi",
    "email": "mario.rossi@test.com",
    "phone": "+39 333 1234567",
    "adults": 2,
    "children": 1,
    "price": 450.00
  }
}
```

#### **Flusso di Elaborazione:**

1. **🔍 Identificazione Host**
   - Il webhook riceve `smoobuUserId`
   - Sistema cerca l'host corrispondente nel database
   - Se non trovato → errore 404

2. **👤 Gestione Cliente**
   - Cerca cliente esistente per email
   - Se non trovato → crea nuovo cliente
   - Associa cliente all'host
   - Salva `smoobuGuestId` per tracking

3. **🏠 Gestione Proprietà**
   - Cerca proprietà per `smoobuApartmentId` o nome
   - Se non trovata → crea nuova proprietà
   - Associa proprietà all'host

4. **📅 Gestione Prenotazione**
   - ID univoco: `smoobu_{smoobuReservationId}`
   - Stati supportati: `confirmed`, `active`, `completed`, `cancelled`
   - Gestione completa: arrivo, partenza, ospiti, prezzo

#### **Azioni Supportate:**

- **`newReservation`** → Crea nuova prenotazione
- **`updateReservation`** → Aggiorna prenotazione esistente
- **`cancelReservation`** → Marca prenotazione come cancellata

### **🏠 Sincronizzazione Proprietà**

#### **Automatica (durante configurazione):**
```json
POST /config/smoobu
{
  "smoobuApiKey": "key",
  "syncProperties": true
}
```

#### **Manuale (quando necessario):**
```json
POST /config/smoobu/sync-properties
```

**Cosa sincronizza:**
- Nome proprietà
- `smoobuApartmentId` per mapping
- Timestamp ultima sincronizzazione
- Metadati di import

### **📊 Monitoraggio e Stato**

#### **Controllo Stato Integrazione:**
```json
GET /config/smoobu/status
```

**Risposta:**
```json
{
  "configured": true,
  "smoobuUserId": 123456,
  "smoobuUserName": "Hotel ABC",
  "configuredAt": "2024-01-15T10:30:00Z",
  "webhookUrl": "https://your-domain.com/webhook/smoobu",
  "syncStats": {
    "lastSyncAt": "2024-01-15T10:30:00Z",
    "propertiesCount": 5,
    "propertiesSynced": 5,
    "syncErrors": 0
  }
}
```

### **🗃️ Struttura Dati nel Database**

#### **Host (users collection):**
```json
{
  "smoobuApiKey": "encrypted-key",
  "smoobuUserId": 123456,
  "smoobuUserName": "Hotel ABC",
  "smoobuUserEmail": "hotel@example.com",
  "smoobuConfiguredAt": "timestamp",
  "lastSmoobuSync": "timestamp",
  "smoobuSyncStats": {
    "lastSyncAt": "timestamp",
    "propertiesCount": 5,
    "propertiesSynced": 5,
    "syncErrors": 0
  }
}
```

#### **Proprietà (users/{hostId}/properties):**
```json
{
  "name": "Appartamento Roma Centro",
  "smoobuApartmentId": 101,
  "importedFrom": "smoobu_sync",
  "lastSyncAt": "timestamp",
  "createdAt": "timestamp"
}
```

#### **Cliente (users collection):**
```json
{
  "email": "mario.rossi@test.com",
  "name": "Mario Rossi",
  "role": "client",
  "assignedHostId": "host-uid",
  "assignedPropertyId": "property-id",
  "smoobuGuestId": 9876,
  "whatsappPhoneNumber": "+39 333 1234567",
  "importedFrom": "smoobu_webhook",
  "createdAt": "timestamp"
}
```

#### **Prenotazione (reservations collection):**
```json
{
  "id": "smoobu_12345",
  "hostId": "host-uid",
  "propertyId": "property-id",
  "propertyName": "Appartamento Roma Centro",
  "clientId": "client-uid",
  "clientName": "Mario Rossi",
  "startDate": "2024-03-15T00:00:00Z",
  "endDate": "2024-03-18T00:00:00Z",
  "status": "confirmed",
  "adults": 2,
  "children": 1,
  "totalPrice": 450.00,
  "smoobuReservationId": 12345,
  "numeroConfermaBooking": "BOOKING_REF_001",
  "smoobuChannelId": 13,
  "smoobuChannelName": "Direct booking",
  "importedFrom": "smoobu_webhook",
  "createdAt": "timestamp"
}
```

### **🧪 Testing dell'Integrazione**

#### **Test Configurazione:**
```bash
# Modifica test/smoobu/test_config_endpoints.js
node test/smoobu/test_config_endpoints.js
```

#### **Test Webhook Locali:**
```bash
# Modifica test/smoobu/test_webhook_smoobu.js  
node test/smoobu/test_webhook_smoobu.js
```

#### **Test Creazione Prenotazioni:**
```bash
# Modifica test/smoobu/test_smoobu_create_booking.js
node test/smoobu/test_smoobu_create_booking.js
```

---

## 🗂️ **INTEGRAZIONE SCIDOO**

### **Caratteristiche**
- ✅ **API Pull-based** (sincronizzazione manuale)
- ✅ **Import Prenotazioni** esistenti
- ✅ **Gestione Clienti** da dati Scidoo
- ✅ **Mapping Proprietà** automatico

### **Configurazione**

**Endpoint:** `POST /config/scidoo`
```json
{
  "scidooApiKey": "your-scidoo-api-key",
  "testConnection": true
}
```

### **Sincronizzazione**

**Endpoint:** `POST /sync/scidoo`
```json
{
  "syncMode": "recent",  // "recent" | "full" | "date_range"
  "daysBack": 30,        // per "recent"
  "dateFrom": "2024-01-01",  // per "date_range"
  "dateTo": "2024-01-31"     // per "date_range"
}
```

---

## 📁 **IMPORT CSV**

### **Supporto File CSV**
- ✅ **Clienti** (Nome, Cognome, Email, Telefono)
- ✅ **Prenotazioni** (Cliente, Alloggio, Date, Stato)
- ✅ **Formato Scidoo** compatibile

### **Endpoint Import**

**Endpoint:** `POST /import-pms-data`
```json
{
  "csvData": "Nome;Cognome;Email;Cellulare\nMario;Rossi;mario@test.com;333123456",
  "importType": "clients"  // "clients" | "reservations"
}
```

---

## 🔧 **Configurazione Server**

### **Variabili d'Ambiente**
```bash
PORT=8080
GOOGLE_CLOUD_PROJECT=giovi-ai
# Firebase credentials gestite via ADC
```

### **Avvio Server**
```bash
cd pms-sync-service
npm install
npm run build
npm start
```

### **Endpoint Health Check**
```bash
curl http://localhost:8080/health
```

---

## 📞 **Troubleshooting**

### **❌ "Host NON TROVATO per smoobuUserId"**
**Causa:** Host non ha configurato l'integrazione Smoobu
**Soluzione:** Eseguire configurazione via `/config/smoobu`

### **❌ "Test connessione fallito"**
**Causa:** API Key non valida o problemi di rete
**Soluzione:** Verificare API Key in Smoobu > Developer

### **❌ "Webhook non arrivano"**
**Causa:** URL webhook non configurato o non raggiungibile
**Soluzione:** 
1. Verificare URL in Smoobu settings
2. Controllare che il server sia pubblicamente accessibile
3. Testare con webhook locali prima

### **❌ "IMPOSSIBILE processare prenotazione perché manca clientId"**
**Causa:** Email cliente non valida
**Soluzione:** Verificare che i dati Smoobu includano email valida

---

## 📈 **Monitoraggio e Logs**

### **Logs Importanti**
```
[SMOOBU_WEBHOOK] Ricevuta azione 'newReservation' per smoobuUser 123
[SMOOBU_WEBHOOK - hostId] Cliente 'email@test.com' creato (ID: xyz)
[SMOOBU_WEBHOOK - hostId] Prenotazione Smoobu ID 12345 salvata con successo
```

### **Metriche da Monitorare**
- Successo webhook (status 200)
- Tempo di elaborazione webhook
- Errori di mapping cliente/proprietà
- Statistiche sincronizzazione proprietà

---

## 🛡️ **Sicurezza**

### **Autenticazione**
- **API Endpoints:** Richiedono Firebase ID Token
- **Webhook Endpoint:** Pubblico (autenticazione via smoobuUserId)

### **Validazione Dati**
- Validazione payload webhook
- Sanitizzazione dati cliente
- Controllo formato email e telefono

### **Rate Limiting**
- Implementare rate limiting per endpoint pubblici
- Monitoring usage API Key Smoobu

---

## 🚀 **Roadmap Future**

### **Prossime Integrazioni**
- [ ] **Booking.com** (via XML/API)
- [ ] **Airbnb** (se API disponibili)
- [ ] **Expedia** integration

### **Miglioramenti Smoobu**
- [ ] Gestione `deleteReservation` action
- [ ] Sincronizzazione bidirezionale prezzi
- [ ] Webhook retry logic
- [ ] Batch webhook processing

### **Performance**
- [ ] Caching proprietà/clienti
- [ ] Database indexing ottimizzato
- [ ] Async webhook processing

---

*Documentazione aggiornata: Gennaio 2024*
*Versione: 1.0 - Integrazione Smoobu Completa* 