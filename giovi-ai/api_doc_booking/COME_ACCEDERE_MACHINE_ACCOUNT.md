# 🔍 Come Accedere al Machine Account Booking.com

**IMPORTANTE:** Se non trovi "Machine Account" cercando nel Provider Portal standard, probabilmente serve un accesso specifico.

---

## ⚠️ Situazione Attuale

Se cerchi "API" nel Provider Portal (`admin.booking.com`) e **non trovi risultati**, significa che:

1. **La sezione Machine Account potrebbe non essere visibile** nel Provider Portal standard
2. **Potrebbe servire un portale separato** (Connectivity Portal)
3. **Il tuo account potrebbe non avere accesso** a questa sezione
4. **Potrebbe essere necessario richiedere accesso** a Booking.com Connectivity Support

---

## 🎯 Come Accedere Effettivamente

### **Opzione 1: Portale Connectivity Separato**

Booking.com potrebbe avere un **portale separato** per Connectivity/API:

1. **Prova a cercare:**
   - `connectivity.booking.com`
   - `api.booking.com`
   - `partner.booking.com/connectivity`
   - `admin.booking.com/connectivity`

2. **Login con le stesse credenziali** del Provider Portal

3. **Cerca:**
   - "Machine account"
   - "API Settings"
   - "Connectivity"

### **Opzione 2: Sezione Nascosta nel Provider Portal**

Nel Provider Portal standard, potrebbe essere in una sezione non evidente:

1. **Prova a cercare:**
   - "Amministrazione" o "Administration"
   - "Impostazioni" o "Settings"
   - "Altro" → Cerca sottomenu "API" o "Connectivity"

2. **Cerca nell'icona profilo** (in alto a destra):
   - Clicca sull'icona profilo utente
   - Cerca "API Settings" o "Connectivity"

3. **Cerca in "Impostazioni"** (se disponibile nel menu)

### **Opzione 3: Contattare Booking.com Connectivity Support**

**Questa è spesso la soluzione più rapida:**

1. **Come contattarli:**
   - **Email:** Cerca "Connectivity Support" nel Provider Portal
   - **Link diretto:** `https://admin.booking.com/` → Cerca "Support" o "Help"
   - **Tramite Partner Help:** Clicca su "Cerca nel Partner Help" che vedi nella ricerca

2. **Cosa dire:**
   ```
   Salve,
   
   Ho bisogno di accesso al Machine Account per configurare le API Booking.com.
   Il mio account è: Deseos Shortrent S.R.L.
   
   Vorrei:
   - Creare/attivare un Machine Account
   - Ottenere credenziali API (username e password)
   - Abilitare gli endpoint:
     - GET /messages/latest (Messaging API)
     - GET /OTA_HotelResNotif (Reservation API)
     - GET /OTA_HotelResModifyNotif (Modified Reservation API)
   
   Potete indicarmi come accedere o come richiedere questo accesso?
   
   Grazie,
   [Tuo nome]
   ```

3. **Tempo di risposta:** 1-2 giorni lavorativi

---

## 🔍 Cosa Cercare Esattamente

### **Nel Provider Portal (`admin.booking.com`):**

Prova a cercare questi termini (uno alla volta):

1. **"Machine account"**
2. **"Connectivity"**
3. **"API"**
4. **"Integration"**
5. **"Amministrazione"** o **"Administration"**
6. **"Impostazioni API"** o **"API Settings"**

### **Se trovi una di queste sezioni:**

- Clicca su quella che trovi
- Cerca "Machine account" o "API Credentials" all'interno

---

## 📞 Cosa Fare ORA

### **Passo 1: Prova Ricerca nel Partner Help**

1. **Nel Provider Portal, cerca:** "machine account" o "API connectivity"
2. **Oppure clicca:** "Cerca nel Partner Help" (che vedi quando cerchi)
3. **Cerca documentazione** su come accedere

### **Passo 2: Contatta Support**

1. **Nel Provider Portal:**
   - Cerca "Support" o "Help" o "Contatta"
   - Oppure vai a: `https://admin.booking.com/help`

2. **Apri ticket/support request:**
   - **Oggetto:** "Richiesta accesso Machine Account per API"
   - **Messaggio:** Usa il template sopra

3. **Includi:**
   - Nome account: Deseos Shortrent S.R.L.
   - Email contatto
   - Scopo: Integrazione API per messaggistica automatica e import prenotazioni

### **Passo 3: Verifica Email**

1. **Controlla email associate** all'account Booking.com
2. **Cerca email da Booking.com** su:
   - Connectivity
   - API access
   - Machine Account
   - Partner API

3. **Potrebbe esserci già un invito** o link di attivazione

---

## 🆘 Alternative Temporanee

Mentre aspetti l'accesso al Machine Account:

### **Opzione 1: Usa Test Environment**

Se disponibile, potresti avere accesso a un ambiente di test dove puoi:
- Testare le API senza credenziali reali
- Fare self-assessment tutorial

### **Opzione 2: Sviluppa con Mock**

Puoi continuare lo sviluppo usando **mock mode** (già implementato nel codice):
- Il sistema funziona con dati mock
- Quando avrai le credenziali, passi a produzione
- Nessun ritardo nello sviluppo

---

## ✅ Checklist: Cosa Fare

- [ ] ✅ Prova ricerca nel Provider Portal: "Machine account", "Connectivity", "API"
- [ ] ✅ Prova ricerca nel Partner Help
- [ ] ✅ Controlla email per inviti o link Booking.com
- [ ] ✅ Contatta Booking.com Connectivity Support
- [ ] ✅ Verifica se esiste portale separato (connectivity.booking.com, etc.)
- [ ] ⏳ Attendi risposta Support (1-2 giorni lavorativi)

---

## 📝 Template Messaggio per Support

**Email a Booking.com Connectivity Support:**

```
Oggetto: Richiesta Accesso Machine Account per API Booking.com

Salve Team Connectivity Support,

Sono [Tuo Nome], responsabile per Deseos Shortrent S.R.L. (Account: [ID account se lo conosci]).

Ho bisogno di accesso al Machine Account per configurare le API Booking.com al fine di:

1. Import automatico delle prenotazioni via Reservation API
2. Gestione automatica dei messaggi guest via Messaging API
3. Risposte automatiche AI ai messaggi dei clienti

Vorrei richiedere:
- Creazione/attivazione di un Machine Account
- Credenziali API (username e password)
- Abilitazione degli endpoint:
  * GET /messages/latest (Messaging API)
  * GET /OTA_HotelResNotif (Reservation API - nuove prenotazioni)
  * GET /OTA_HotelResModifyNotif (Reservation API - modifiche/cancellazioni)

Nel Provider Portal (admin.booking.com) non trovo la sezione "Machine Account" cercando "API" o "Connectivity".

Potete indicarmi:
1. Come accedere al Machine Account?
2. È necessario un portale separato?
3. Serve una richiesta di accesso specifica?

Grazie per l'assistenza,
[Tuo Nome]
[Email]
[Numero telefono opzionale]
```

---

## 🎯 Conclusione

**Se non trovi "Machine Account" cercando nel Provider Portal standard:**

1. ✅ **Contatta Booking.com Connectivity Support** - questa è la soluzione più rapida
2. ✅ **Verifica email** per eventuali inviti/link
3. ✅ **Continua sviluppo con mock** mentre aspetti credenziali

**Tempo stimato per ottenere accesso:** 1-2 giorni lavorativi dopo richiesta Support

---

**Ultima modifica:** 2025-01-20

