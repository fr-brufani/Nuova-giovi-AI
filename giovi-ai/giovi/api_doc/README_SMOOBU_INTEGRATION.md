# 🏨 Integrazione Smoobu - Documentazione Funzionamento

## ✅ **STATO: INTEGRAZIONE OPERATIVA**
**Data Completamento:** Settembre 2024  
**Versione:** 1.0 - Stabile in Produzione  
**Tipo:** Webhook Real-time

## 🎯 **Panoramica**

L'integrazione Smoobu è **completamente funzionante** e permette la sincronizzazione real-time tra Smoobu e il database giovi_ai attraverso:
- **Configurazione automatica** via frontend
- **Import automatico** di proprietà e prenotazioni esistenti  
- **Webhook real-time** per aggiornamenti istantanei

---

## 🔄 **Flusso Completo di Integrazione**

### **FASE 1: Configurazione Iniziale (Frontend)**

**1.1 - Host inserisce API Key:**
- Host accede a **Impostazioni** nell'app giovi_ai
- Sezione **"Integrazioni Gestionali PMS"**
- Seleziona **"Smoobu"** dal dropdown
- Inserisce API Key di Smoobu
- Clicca **"Testa Connessione"**

**1.2 - Processo Automatico Server:**
```
POST /config/smoobu
├── Test API Key con Smoobu
├── Recupero info account (nome, email, user_id)
├── Import automatico TUTTE le proprietà
├── Salvataggio dati in Firebase
├── Generazione URL webhook
└── Risposta con esito e statistiche
```

**1.3 - Risultato:**
- ✅ Tutte le proprietà Smoobu → importate in giovi_ai
- ✅ Dati account salvati nel profilo host
- ✅ URL webhook generato per configurazione manuale

---

### **FASE 2: Configurazione Webhook Smoobu**

**2.1 - Host configura Webhook in Smoobu:**
1. Accede a https://login.smoobu.com
2. Va in **Impostazioni** → **API** → **Webhook**
3. Inserisce URL: `https://pms-sync-service-zuxzockfdq-ew.a.run.app/webhook/smoobu`
4. Abilita eventi: `newReservation`, `updateReservation`, `cancelReservation`, `deleteReservation`

**2.2 - Test Webhook:**
- Crea una prenotazione di test in Smoobu
- Verifica ricezione nel database giovi_ai

---

### **FASE 3: Sincronizzazione Real-time**

Quando accade qualsiasi evento in Smoobu, il webhook invia automaticamente:

#### **📥 Nuova Prenotazione (`newReservation`)**
```json
{
  "action": "newReservation",
  "user": 1306068,
  "data": {
    "id": 102483793,
    "arrival": "2025-01-15",
    "departure": "2025-01-18", 
    "apartment": {"id": 101, "name": "Gialla"},
    "guest-name": "Francesco Brufani",
    "email": "fra.brufani@gmail.com"
  }
}
```

**Processo Automatico:**
1. ✅ **Identificazione Host** via `smoobuUserId`
2. ✅ **Trova/Crea Cliente** usando email
3. ✅ **Trova/Crea Proprietà** usando `apartment.id`
4. ✅ **Crea Prenotazione** in Firestore
5. ✅ **Link Cliente-Host-Proprietà**

#### **📝 Aggiornamento Prenotazione (`updateReservation`)**
- Stesso formato di `newReservation`
- Aggiorna prenotazione esistente in base a `smoobu_reservation_id`
- Aggiorna dati cliente se modificati

#### **❌ Cancellazione Prenotazione (`cancelReservation`)**
- Cambia stato prenotazione in "cancelled"
- Mantiene dati storici per analytics

#### **🗑️ Eliminazione Prenotazione (`deleteReservation`)**
- Elimina completamente la prenotazione dal database
- Solo se esiste, altrimenti ignora

---

## 📊 **Cosa Viene Salvato nel Database**

### **Collection: `users` (Host)**
```firestore
{
  "uid": "g27jLEwsj8UgNSF537wiHMcn2di1",
  "role": "host",
  "smoobuApiKey": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "smoobuUserId": 1306068,
  "smoobuUserName": "Hotel Paradise",
  "smoobuUserEmail": "info@hotelparadise.com",
  "smoobuConfiguredAt": "2025-01-07T10:35:47.000Z",
  "smoobuSyncStats": {
    "totalProperties": 3,
    "totalReservations": 156,
    "lastSyncAt": "2025-01-07T10:35:47.000Z"
  }
}
```

### **Collection: `properties`**
```firestore
{
  "id": "ekcKHmtUkpJyEdcWHXOv",
  "name": "Gialla",
  "smoobuApartmentId": 101,
  "importedFrom": "smoobu",
  "hostId": "g27jLEwsj8UgNSF537wiHMcn2di1",
  "createdAt": "2025-01-07T10:35:47.000Z",
  "lastSyncAt": "2025-01-07T10:35:47.000Z"
}
```

### **Collection: `users` (Cliente)**
```firestore
{
  "uid": "Kgco0qCdLX53TvkqWKLZ",
  "email": "fra.brufani@gmail.com",
  "name": "Francesco Brufani",
  "role": "client",
  "assignedHostId": "g27jLEwsj8UgNSF537wiHMcn2di1",
  "assignedPropertyId": "ekcKHmtUkpJyEdcWHXOv",
  "smoobuGuestId": 789456,
  "importedFrom": "smoobu",
  "createdAt": "2025-01-07T09:35:47.000Z"
}
```

### **Collection: `reservations`**
```firestore
{
  "id": "smoobu_102483793",
  "smoobuReservationId": 102483793,
  "smoobuReferenceId": "ABC123",
  "clientId": "Kgco0qCdLX53TvkqWKLZ",
  "propertyId": "ekcKHmtUkpJyEdcWHXOv", 
  "hostId": "g27jLEwsj8UgNSF537wiHMcn2di1",
  "checkIn": "2025-01-15",
  "checkOut": "2025-01-18",
  "guests": 2,
  "totalPrice": 450.00,
  "status": "confirmed",
  "importedFrom": "smoobu",
  "createdAt": "2025-01-07T09:35:47.000Z",
  "lastSyncAt": "2025-01-07T09:35:47.000Z"
}
```

---

## 🔧 **Endpoints API Implementati**

### **Configurazione**
- `POST /config/smoobu` - Configurazione automatica completa
- `POST /config/smoobu/test` - Test connessione senza salvare
- `GET /config/smoobu/status` - Stato attuale integrazione
- `POST /config/smoobu/sync-properties` - Risincronizzazione proprietà

### **Webhook Real-time**  
- `POST /webhook/smoobu` - Riceve eventi da Smoobu

### **Monitoraggio**
- `GET /config/smoobu/stats` - Statistiche sincronizzazione

---

## ✅ **Vantaggi dell'Integrazione**

1. **🔄 Sincronizzazione Real-time**
   - Aggiornamenti istantanei senza intervento manuale
   - Zero ritardi tra Smoobu e giovi_ai

2. **🤖 Configurazione Automatica**
   - Un clic per importare tutto l'account Smoobu
   - Zero configurazione manuale di proprietà

3. **🔗 Linking Intelligente**
   - Auto-assegnazione clienti a host e proprietà
   - Gestione automatica duplicati

4. **📊 Monitoraggio Completo**
   - Statistiche dettagliate sincronizzazione
   - Log completi per debugging

5. **🛡️ Gestione Errori Robusta**
   - Retry automatici
   - Logging dettagliato errori
   - Graceful handling di dati mancanti

---

## 🎯 **Test e Verifica**

### **Test Configurazione:**
1. Host inserisce API Key → Verifica import proprietà
2. Controlla collection `properties` in Firebase
3. Verifica dati host aggiornati con info Smoobu

### **Test Webhook:**
1. Crea prenotazione di test in Smoobu
2. Verifica log server: `Ricevuta azione 'newReservation'`
3. Controlla collection `reservations` in Firebase
4. Verifica creazione/aggiornamento cliente in `users`

### **Test Aggiornamento:**
1. Modifica prenotazione in Smoobu
2. Verifica aggiornamento automatico in Firebase

### **Test Cancellazione:**
1. Cancella prenotazione in Smoobu  
2. Verifica cambio stato in Firebase

---

## 🚨 **Troubleshooting**

### **Webhook non funziona:**
- ✅ URL deve essere HTTPS (non HTTP)
- ✅ Verifica eventi abilitati in Smoobu
- ✅ Controlla log Cloud Run per errori

### **Import proprietà fallisce:**
- ✅ Verifica validità API Key
- ✅ Controlla permissions API Key in Smoobu
- ✅ Verifica connessione internet

### **Prenotazioni non sincronizzate:**
- ✅ Verifica mapping smoobuUserId nel database
- ✅ Controlla formato dati webhook
- ✅ Verifica log errori server

---

## 📈 **Statistiche Monitoraggio**

L'integrazione traccia automaticamente:
- Numero proprietà sincronizzate
- Numero prenotazioni importate
- Timestamp ultima sincronizzazione
- Statistiche webhook ricevuti/processati
- Log errori dettagliati

Tutti i dati sono disponibili tramite `/config/smoobu/stats` per monitoring e analytics. 