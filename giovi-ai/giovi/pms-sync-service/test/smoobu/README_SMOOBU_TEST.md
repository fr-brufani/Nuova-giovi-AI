# 🏨 Guida al Testing dell'Integrazione Smoobu

Questa guida ti mostra come testare che l'integrazione Smoobu funzioni correttamente con il tuo sistema.

## 📋 Prerequisiti

1. **Account Smoobu di prova** con API Key
2. **Firebase configurato** con il tuo progetto
3. **pms-sync-service** funzionante
4. **Almeno un appartamento** configurato in Smoobu

## 🚀 Processo di Testing

### Step 1: Recupera il tuo smoobuUserId

```bash
# 1. Modifica test/smoobu/test_smoobu_user.js e inserisci la tua API Key
# 2. Esegui lo script dalla cartella principale pms-sync-service
node test/smoobu/test_smoobu_user.js
```

Lo script ti mostrerà:
- ✅ Il tuo `smoobuUserId` (es. 123)
- 🏠 Gli appartamenti disponibili con i loro ID

### Step 2: Configura l'Host nel Database

Nel database Firebase, aggiorna il documento dell'host aggiungendo:

```json
{
  "smoobuUserId": 123,
  "role": "host",
  // altri campi esistenti...
}
```

⚠️ **IMPORTANTE**: Sostituisci `123` con il tuo vero `smoobuUserId` ottenuto dal Step 1.

### Step 3: Avvia il pms-sync-service

```bash
# Nella cartella pms-sync-service
npm run build
npm start
```

Il servizio dovrebbe avviarsi su `http://localhost:8080`

### Step 4A: Test Locale dei Webhook (Raccomandato)

Per testare rapidamente senza configurare webhooks reali:

```bash
# 1. Modifica test/smoobu/test_webhook_smoobu.js e inserisci il tuo smoobuUserId
# 2. Esegui il test dalla cartella principale pms-sync-service
node test/smoobu/test_webhook_smoobu.js
```

Questo script simula i webhook di Smoobu inviando payload di test al tuo servizio locale.

### Step 4B: Test con Webhook Reali (Opzionale)

Se vuoi testare con webhook reali da Smoobu:

#### 4B.1: Esponi il servizio pubblicamente

```bash
# Installa ngrok se non ce l'hai
npm install -g ngrok

# Esponi il servizio su porta 8080
ngrok http 8080
```

Copia l'URL pubblico (es. `https://abc123.ngrok.io`)

#### 4B.2: Configura Webhook in Smoobu

1. Vai nelle **impostazioni Smoobu**
2. Sezione **API/Webhook**
3. Inserisci URL: `https://abc123.ngrok.io/webhook/smoobu`
4. Salva le impostazioni

#### 4B.3: Crea prenotazioni di test

```bash
# 1. Modifica test/smoobu/test_smoobu_create_booking.js
#    - Inserisci la tua API Key
#    - Inserisci un apartment ID valido
# 2. Esegui il test completo dalla cartella principale pms-sync-service
node test/smoobu/test_smoobu_create_booking.js --complete
```

## 🔍 Verifiche di Successo

### Nei Log del Server

Dovresti vedere log simili a:

```
[SMOOBU_WEBHOOK] Ricevuta azione 'newReservation' per smoobuUser 123, prenotazione Smoobu ID 12345
[SMOOBU_WEBHOOK - hostId] Cliente 'mario.rossi@test.com' creato (ID: xyz)
[SMOOBU_WEBHOOK - hostId] Proprietà 'Appartamento Test' creata (ID: abc)
[SMOOBU_WEBHOOK - hostId] Prenotazione Smoobu ID 12345 salvata con successo in Firestore
```

### Nel Database Firebase

#### Collezione `users`
Nuovo documento cliente:
```json
{
  "email": "mario.rossi@test.com",
  "name": "Mario Rossi",
  "role": "client",
  "assignedHostId": "hostId",
  "smoobuGuestId": 9876,
  "importedFrom": "smoobu_webhook"
}
```

#### Collezione `users/{hostId}/properties`
Nuova proprietà:
```json
{
  "name": "Appartamento Test Roma",
  "smoobuApartmentId": 101,
  "importedFrom": "smoobu_webhook"
}
```

#### Collezione `reservations`
Nuova prenotazione con ID `smoobu_12345`:
```json
{
  "hostId": "hostId",
  "propertyId": "propertyId",
  "clientId": "clientId",
  "startDate": "2024-03-15T00:00:00Z",
  "endDate": "2024-03-18T00:00:00Z",
  "status": "confirmed",
  "smoobuReservationId": 12345,
  "numeroConfermaBooking": "TEST_BOOKING_001",
  "importedFrom": "smoobu_webhook"
}
```

## 🛠 Troubleshooting

### ❌ "Host NON TROVATO per smoobuUserId"

**Problema**: Il webhook non trova l'host configurato.

**Soluzione**:
1. Verifica che lo `smoobuUserId` nel database sia corretto
2. Controlla che l'host abbia `role: "host"`
3. Assicurati di aver usato il vero `smoobuUserId` dal Step 1

### ❌ "IMPOSSIBILE processare prenotazione perché manca clientId"

**Problema**: Email cliente non valida o mancante.

**Soluzione**: Verifica che i dati di test includano un'email valida.

### ❌ Webhook non arrivano

**Problema**: Smoobu non riesce a raggiungere il tuo servizio.

**Soluzioni**:
1. Verifica che ngrok sia attivo
2. Controlla che l'URL webhook sia configurato correttamente in Smoobu
3. Verifica che il pms-sync-service sia in esecuzione
4. Testa prima con `test_webhook_smoobu.js` (test locale)

### ❌ Errori di autenticazione Firebase

**Problema**: Credenziali Firebase non configurate.

**Soluzione**: Assicurati che le credenziali Firebase siano configurate correttamente.

## 📊 Test Completo di Successo

Un test completo di successo dovrebbe mostrare:

1. ✅ **Webhook newReservation** → Cliente e prenotazione creati
2. ✅ **Webhook updateReservation** → Prenotazione aggiornata
3. ✅ **Webhook cancelReservation** → Prenotazione marcata come cancellata

Se tutti questi passaggi funzionano, la tua integrazione Smoobu è operativa! 🎉

## 🔧 File di Test Inclusi

- `test/smoobu/test_smoobu_user.js` - Recupera info utente e appartamenti
- `test/smoobu/test_webhook_smoobu.js` - Simula webhook localmente  
- `test/smoobu/test_smoobu_create_booking.js` - Crea prenotazioni reali via API
- `test/smoobu/test_config_endpoints.js` - ⭐ **NUOVO** - Test degli endpoint di configurazione

## 🚀 **NUOVO: Configurazione Automatica (Recommended)**

### **Con Solo l'API Key - Tutto Automatico!**

Il nuovo sistema permette configurazione **completamente automatica** con solo l'API Key:

#### **Endpoint Disponibili:**

```bash
# Test connessione (senza salvare)
POST /config/smoobu/test
{
  "smoobuApiKey": "your-api-key"
}

# Configurazione completa automatica
POST /config/smoobu
{
  "smoobuApiKey": "your-api-key",
  "testConnection": true,
  "syncProperties": true
}

# Stato integrazione
GET /config/smoobu/status

# Sincronizzazione manuale proprietà
POST /config/smoobu/sync-properties
```

#### **Cosa Fa Automaticamente:**

1. ✅ **Testa API Key** chiamando Smoobu
2. ✅ **Recupera User ID** automaticamente
3. ✅ **Sincronizza tutte le proprietà** esistenti
4. ✅ **Salva configurazione** nel database
5. ✅ **Fornisce URL webhook** pronto per Smoobu
6. ✅ **Monitoraggio** stato e statistiche

#### **Test degli Endpoint:**

```bash
# Modifica test/smoobu/test_config_endpoints.js con:
# - La tua API Key Smoobu
# - Il tuo JWT token Firebase

node test/smoobu/test_config_endpoints.js
```

### **Flusso Completo per l'Host:**

1. **Host inserisce solo API Key** nel frontend
2. **Sistema fa tutto automaticamente**
3. **Host copia URL webhook** in Smoobu
4. **🎉 Integrazione attiva!**

## 📞 Supporto

Se incontri problemi, controlla:
1. I log del pms-sync-service per errori dettagliati
2. La configurazione Firebase
3. Le credenziali Smoobu
4. La documentazione ufficiale Smoobu: https://docs.smoobu.com/ 