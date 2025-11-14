# 🔄 Flusso Completo - Email Agent Service

## 📋 Panoramica del Sistema

Abbiamo sviluppato un sistema per automatizzare il customer care tramite email per i property manager. Il sistema gestisce:
1. **Connessione Gmail** (OAuth)
2. **Import storico email** (Backfill)
3. **Parsing email** (Booking/Airbnb)
4. **Integrazione con Firestore**

## ✅ Cosa è STATO SVILUPPATO (Step 1-3)

### **Step 1: Setup Base** ✅
- ✅ Servizio FastAPI configurato
- ✅ Integrazione Firebase/Firestore
- ✅ Health check endpoint
- ✅ CORS configurato per frontend

### **Step 2: OAuth Gmail** ✅
- ✅ Endpoint `POST /integrations/gmail/start` - Inizia flusso OAuth
- ✅ Endpoint `POST /integrations/gmail/callback` - Completa OAuth
- ✅ Cifratura token (Fernet)
- ✅ Salvataggio integrazione in Firestore (`hostEmailIntegrations`)

### **Step 3: Backfill & Parsing** ✅
- ✅ Endpoint `POST /integrations/gmail/{email}/backfill` - Import storico
- ✅ Parser Booking.com (conferme + messaggi)
- ✅ Parser Airbnb (conferme + messaggi)
- ✅ Deduplica messaggi processati
- ✅ Salvataggio in `processedMessageIds`

### **Frontend** ✅
- ✅ Pagina Impostazioni con `GmailIntegrationCard`
- ✅ Pagina callback OAuth (`/integrations/gmail/callback`)
- ✅ Integrazione con email-agent-service
- ✅ UI per OAuth e Backfill

## 🔄 FLUSSO COMPLETO - Cosa Dovrebbe Funzionare

### **1. FLUSSO OAUTH GMAIL** ✅ (Dovrebbe Funzionare)

```
Utente → Frontend → Backend → Google OAuth → Frontend → Backend → Firestore
```

**Passi:**
1. ✅ Utente va su `/impostazioni`
2. ✅ Inserisce email Gmail nella card "Connessione Email"
3. ✅ Clicca "Collega Gmail"
4. ✅ Frontend chiama `POST /integrations/gmail/start` con:
   - `hostId`: ID dell'host
   - `email`: indirizzo Gmail
   - `redirectUri`: `http://localhost:8080/integrations/gmail/callback`
5. ✅ Backend genera URL OAuth Google e salva state in Firestore
6. ✅ Frontend apre popup con URL Google OAuth
7. ✅ Utente autorizza accesso Gmail su Google
8. ✅ Google reindirizza a `/integrations/gmail/callback?code=...&state=...`
9. ✅ Frontend chiama `POST /integrations/gmail/callback` con:
   - `state`: state ricevuto da Google
   - `code`: authorization code
   - `hostId`: ID host
   - `email`: indirizzo Gmail
10. ✅ Backend scambia code per token, cifra token, salva in Firestore
11. ✅ Integrazione completata! Stato: `connected` in `hostEmailIntegrations/{email}`

**Cosa dovresti vedere:**
- ✅ Popup Google OAuth si apre
- ✅ Autorizzazione completata
- ✅ Card mostra "Email collegata" con stato verde
- ✅ In Firestore: documento `hostEmailIntegrations/{email}` con token cifrati

### **2. FLUSSO BACKFILL EMAIL** ✅ (Dovrebbe Funzionare)

```
Utente → Frontend → Backend → Gmail API → Parser → Firestore
```

**Passi:**
1. ✅ Utente ha già collegato Gmail (OAuth completato)
2. ✅ Clicca "Importa email prenotazioni" nella card Gmail
3. ✅ Frontend chiama `POST /integrations/gmail/{email}/backfill?host_id={hostId}`
4. ✅ Backend:
   - Recupera token cifrato da Firestore
   - Decifra token
   - Chiama Gmail API per ultimi 6 mesi
   - Filtra email da Booking/Airbnb
   - Per ogni email:
     - Verifica se già processata (`processedMessageIds`)
     - Passa ai parser (Booking/Airbnb)
     - Estratte info prenotazione/messaggio
     - Marca come processata
5. ✅ Backend restituisce risultati con:
   - `processed`: numero email processate
   - `items`: array di email parse (`ParsedEmail`)

**Cosa dovresti vedere:**
- ✅ Toast con "Import completato. Processate X email"
- ✅ In console backend: log di email processate
- ✅ In Firestore: sottocollezione `processedMessageIds` con ID email processate

### **3. FLUSSO PARSING EMAIL** ✅ (Dovrebbe Funzionare)

**Email Booking.com Conferma:**
- ✅ Estrae: `reservationId`, `propertyName`, `checkIn`, `checkOut`, `guestName`, `guestEmail`, `totalAmount`
- ✅ Tipo: `booking_confirmation`

**Email Booking.com Messaggio:**
- ✅ Estrae: `reservationId`, `message`, `replyTo`
- ✅ Tipo: `booking_message`

**Email Airbnb Conferma:**
- ✅ Estrae: `threadId`, `propertyName`, `checkIn`, `checkOut`, `guestName`, `guestEmail`, `totalAmount`
- ✅ Tipo: `airbnb_confirmation`

**Email Airbnb Messaggio:**
- ✅ Estrae: `threadId`, `message`, `guestName`, `replyTo`
- ✅ Tipo: `airbnb_message`

## ❌ Cosa NON È ANCORA IMPLEMENTATO (Step 4-8)

### **Step 4: Persistenza Automatica** ❌
- ❌ Salvataggio automatico prenotazioni in `reservations`
- ❌ Salvataggio automatico clienti in `clients`
- ❌ Salvataggio automatico property in `properties`
- **Stato attuale:** Il parsing funziona ma i dati non vengono salvati in Firestore

### **Step 5: Gmail Watch** ❌
- ❌ Setup Gmail watch per notifiche real-time
- ❌ Endpoint per gestire notifiche Pub/Sub da Gmail
- ❌ Refresh automatico watch (ogni 7 giorni)

### **Step 6: Pipeline Messaggi Guest** ❌
- ❌ Rilevamento messaggi guest in tempo reale
- ❌ Verifica `autoReplyEnabled` per cliente
- ❌ Estrazione contesto conversazione

### **Step 7: Integrazione Gemini AI** ❌
- ❌ Chiamata a Gemini per generare risposte
- ❌ Costruzione prompt con contesto
- ❌ Gestione conversazioni

### **Step 8: Invio Email Reply** ❌
- ❌ Invio email reply tramite Gmail API
- ❌ Salvataggio risposte AI in Firestore
- ❌ Tracking messaggi inviati

## 🐛 PROBLEMA: File non si aggiorna

Hai detto che quando provi a configurare mail, il file non si aggiorna. Questo potrebbe essere perché:

1. **Il componente `GmailIntegrationCard` legge da Firestore** (`useGmailIntegration` hook)
2. **Dopo OAuth callback**, l'integrazione viene salvata in Firestore
3. **Il componente dovrebbe aggiornarsi automaticamente** tramite `onSnapshot` listener
4. **Se non si aggiorna**, potrebbe essere:
   - Firestore listener non funziona
   - Il documento non viene salvato correttamente
   - Problema con `hostId` (non corrisponde)

**Verifica:**
- Controlla Firestore: esiste `hostEmailIntegrations/{email}`?
- Controlla console browser: ci sono errori?
- Controlla `hostId`: è corretto?

## 📊 Test Completo - Cosa Verificare

### **Test 1: OAuth Flow** ✅ (Dovrebbe Funzionare)
- [ ] Popup OAuth si apre
- [ ] Autorizzazione completata
- [ ] Card mostra "Email collegata"
- [ ] Firestore contiene integrazione

### **Test 2: Backfill** ✅ (Dovrebbe Funzionare)
- [ ] Click "Importa email prenotazioni"
- [ ] Toast "Import completato"
- [ ] Backend log mostra email processate
- [ ] Firestore contiene `processedMessageIds`

### **Test 3: Parsing** ✅ (Dovrebbe Funzionare)
- [ ] Email Booking conferma → parser estrae dati
- [ ] Email Booking messaggio → parser estrae dati
- [ ] Email Airbnb conferma → parser estrae dati
- [ ] Email Airbnb messaggio → parser estrae dati

### **Test 4: Persistenza** ❌ (NON Funziona)
- [ ] Prenotazioni salvate in `reservations` ❌
- [ ] Clienti salvati in `clients` ❌
- [ ] Property salvate in `properties` ❌

### **Test 5: Watch** ❌ (NON Funziona)
- [ ] Gmail watch attivo ❌
- [ ] Nuove email triggerano notifica ❌

### **Test 6: AI Reply** ❌ (NON Funziona)
- [ ] Messaggio guest → verifica autoReplyEnabled ❌
- [ ] Chiamata Gemini ❌
- [ ] Invio risposta ❌

## 🚀 Prossimi Passi

1. **Step 4**: Implementare persistenza automatica (prenotazioni/clienti/property)
2. **Step 5**: Implementare Gmail watch
3. **Step 6-8**: Pipeline completa AI reply

